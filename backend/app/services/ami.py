"""Asterisk AMI (Manager Interface) -- клиент для отслеживания звонков.

Подключается к AMI по TCP, слушает события и создаёт/завершает CallSession
через SessionManager. Оповещает дашборд через WebSocket broadcast.

Архитектура:
  AMI (события) -> SessionManager -> WebSocket -> Dashboard
  BridgeEnter -> AMI Originate -> AudioSocket -> STT -> CallSession.transcript
"""

import asyncio
import logging
import time
from typing import Optional

from config import settings
from app.models.call_session import (
    CallDirection,
    CallStatus,
    SessionManager,
    session_manager,
)
from app.core.ws_manager import DashboardConnectionManager, ws_manager

logger = logging.getLogger(__name__)

# Фильтр каналов: пропускаем служебные (Local/, PJSIP/echo и т.д.)
_IGNORED_CHANNEL_PREFIXES = ("Local/",)


def _parse_ami_message(raw: str) -> dict[str, str]:
    """Парсинг AMI-сообщения (формат 'Key: Value' через CRLF)."""
    result = {}
    for line in raw.strip().split("\r\n"):
        if ": " in line:
            key, _, value = line.partition(": ")
            result[key] = value
    return result


def _extract_endpoint(channel: str) -> str:
    """Извлечь имя endpoint из канала ('PJSIP/manager-00000001' -> 'manager')."""
    if "/" in channel:
        name = channel.split("/", 1)[1]
        if "-" in name:
            name = name.rsplit("-", 1)[0]
        return name
    return channel


def _should_ignore_channel(channel: str) -> bool:
    """Пропускать ли канал (служебные, эхо-тест и т.д.)."""
    for prefix in _IGNORED_CHANNEL_PREFIXES:
        if channel.startswith(prefix):
            return True
    return False


class AsteriskAMIClient:
    """Asyncio-клиент Asterisk AMI для мониторинга звонков."""

    def __init__(
        self,
        sm: SessionManager,
        wm: DashboardConnectionManager,
        host: str = "127.0.0.1",
        port: int = 5038,
        username: str = "salespilot",
        secret: str = "",
    ):
        self._sm = sm
        self._wm = wm
        self._host = host
        self._port = port
        self._username = username
        self._secret = secret

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._task: Optional[asyncio.Task] = None
        self._connected = False
        self._running = False

        # Маппинг Asterisk Uniqueid -> call_id (в SessionManager)
        self._channel_map: dict[str, str] = {}
        # Маппинг Asterisk Uniqueid -> channel name (для логов)
        self._channel_names: dict[str, str] = {}
        # Маппинг Linkedid -> call_id (группировка каналов одного звонка)
        self._linked_map: dict[str, str] = {}
        # Трекинг AudioSocket Originate (чтобы не дублировать)
        self._audiosocket_originated: set[str] = set()

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def start(self) -> None:
        """Запустить клиент как фоновую задачу."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AMI: клиент запущен")

    async def stop(self) -> None:
        """Остановить клиент и закрыть соединение."""
        self._running = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("AMI: клиент остановлен")

    async def _run_loop(self) -> None:
        """Основной цикл: подключение + переподключение при обрыве."""
        while self._running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                logger.error(f"AMI: ошибка соединения: {e}")
                if self._running:
                    logger.info("AMI: переподключение через 5 сек...")
                    await asyncio.sleep(5)

    async def _connect_and_listen(self) -> None:
        """Подключиться к AMI, залогиниться, слушать события."""
        logger.info(f"AMI: подключение к {self._host}:{self._port}...")

        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port
        )

        # Прочитать приветствие
        greeting = await self._reader.readline()
        logger.info(f"AMI: {greeting.decode().strip()}")

        # Логин
        await self._send_action({
            "Action": "Login",
            "Username": self._username,
            "Secret": self._secret,
        })

        login_response = await self._read_message()
        if login_response.get("Response") != "Success":
            raise ConnectionError(
                f"AMI: логин не удался: {login_response.get('Message', 'unknown')}"
            )

        self._connected = True
        logger.info("AMI: подключён к Asterisk, слушаю события звонков")

        # Основной цикл чтения событий
        while self._running:
            msg = await self._read_message()
            if not msg:
                break
            if "Event" in msg:
                await self._handle_event(msg)

    async def _send_action(self, action: dict[str, str]) -> None:
        """Отправить AMI-action."""
        lines = [f"{k}: {v}" for k, v in action.items()]
        data = "\r\n".join(lines) + "\r\n\r\n"
        self._writer.write(data.encode())
        await self._writer.drain()

    async def _read_message(self) -> dict[str, str]:
        """Прочитать одно AMI-сообщение (до пустой строки)."""
        lines = []
        while True:
            try:
                line = await asyncio.wait_for(
                    self._reader.readline(), timeout=30
                )
            except asyncio.TimeoutError:
                # Heartbeat -- отправляем Ping
                await self._send_action({"Action": "Ping"})
                continue

            if not line:
                # Соединение закрыто
                return {}

            decoded = line.decode("utf-8", errors="replace").rstrip("\r\n")
            if decoded == "":
                break
            lines.append(decoded)

        return _parse_ami_message("\r\n".join(lines))

    async def _handle_event(self, event: dict[str, str]) -> None:
        """Обработка AMI-события."""
        event_name = event.get("Event", "")

        if event_name == "DialBegin":
            await self._on_dial_begin(event)
        elif event_name == "DialEnd":
            await self._on_dial_end(event)
        elif event_name == "BridgeEnter":
            await self._on_bridge_enter(event)
        elif event_name == "Hangup":
            await self._on_hangup(event)

    async def _on_dial_begin(self, event: dict[str, str]) -> None:
        """DialBegin: создаём новую сессию звонка."""
        channel = event.get("Channel", "")
        dest_channel = event.get("DestChannel", "")
        uniqueid = event.get("Uniqueid", "")
        linkedid = event.get("Linkedid", "")

        if _should_ignore_channel(channel) or _should_ignore_channel(dest_channel):
            return

        # Определяем участников
        caller_endpoint = _extract_endpoint(channel)
        callee_endpoint = _extract_endpoint(dest_channel)
        caller_num = event.get("CallerIDNum", caller_endpoint)
        caller_name = event.get("CallerIDName", "")
        callee_num = event.get("DestCallerIDNum", callee_endpoint)
        callee_name = event.get("DestCallerIDName", "")

        # Определяем направление
        # Если звонящий -- наш менеджер, это исходящий; иначе входящий
        direction = CallDirection.OUTBOUND  # по умолчанию между расширениями

        session = self._sm.create_session(
            direction=direction,
            status=CallStatus.RINGING,
            caller_number=caller_num,
            caller_name=caller_name if caller_name != "<unknown>" else caller_endpoint,
            callee_number=callee_num,
            callee_name=callee_name if callee_name != "<unknown>" else callee_endpoint,
            manager_extension=callee_endpoint,
        )

        # Сохраняем маппинги
        self._channel_map[uniqueid] = session.call_id
        self._channel_names[uniqueid] = channel
        self._linked_map[linkedid] = session.call_id

        # Также маппим destination channel
        dest_uniqueid = event.get("DestUniqueid", "")
        if dest_uniqueid:
            self._channel_map[dest_uniqueid] = session.call_id
            self._channel_names[dest_uniqueid] = dest_channel

        logger.info(
            f"AMI: DialBegin -- {caller_endpoint} -> {callee_endpoint} "
            f"(call_id={session.call_id[:8]})"
        )

        await self._broadcast_update()

    async def _on_dial_end(self, event: dict[str, str]) -> None:
        """DialEnd: звонок отвечен или отклонён."""
        uniqueid = event.get("Uniqueid", "")
        dial_status = event.get("DialStatus", "")

        call_id = self._channel_map.get(uniqueid)
        if not call_id:
            # Попробуем через linkedid
            linkedid = event.get("Linkedid", "")
            call_id = self._linked_map.get(linkedid)

        if not call_id:
            return

        session = self._sm.get_session(call_id)
        if not session:
            return

        if dial_status == "ANSWER":
            session.status = CallStatus.ACTIVE
            session.answered_at = time.time()
            logger.info(f"AMI: DialEnd ANSWER (call_id={call_id[:8]})")
        elif dial_status in ("CANCEL", "NOANSWER", "BUSY", "CONGESTION"):
            # Звонок не состоялся -- завершаем сессию
            self._sm.end_session(call_id)
            logger.info(f"AMI: DialEnd {dial_status} (call_id={call_id[:8]})")

        await self._broadcast_update()

    async def _on_bridge_enter(self, event: dict[str, str]) -> None:
        """BridgeEnter: канал вошёл в мост (разговор начался). Запускаем AudioSocket."""
        uniqueid = event.get("Uniqueid", "")
        linkedid = event.get("Linkedid", "")
        channel = event.get("Channel", "")

        # Пропускаем Local-каналы (наши же Originate)
        if _should_ignore_channel(channel):
            return

        call_id = self._channel_map.get(uniqueid) or self._linked_map.get(linkedid)
        if not call_id:
            return

        session = self._sm.get_session(call_id)
        if session and session.status == CallStatus.RINGING:
            session.status = CallStatus.ACTIVE
            session.answered_at = session.answered_at or time.time()
            logger.info(f"AMI: BridgeEnter (call_id={call_id[:8]})")
            await self._broadcast_update()

        # Запускаем AudioSocket один раз на звонок (BridgeEnter приходит дважды)
        if call_id not in self._audiosocket_originated:
            self._audiosocket_originated.add(call_id)
            await self._originate_audiosocket(call_id, channel)

    async def _on_hangup(self, event: dict[str, str]) -> None:
        """Hangup: канал закрыт. Завершаем сессию, если оба канала положили трубку."""
        uniqueid = event.get("Uniqueid", "")
        linkedid = event.get("Linkedid", "")

        call_id = self._channel_map.get(uniqueid) or self._linked_map.get(linkedid)
        if not call_id:
            return

        session = self._sm.get_session(call_id)
        if not session:
            # Уже завершён (первый Hangup из пары мог его завершить)
            return

        # Проверяем, есть ли ещё активные каналы для этого звонка
        remaining_channels = [
            uid for uid, cid in self._channel_map.items()
            if cid == call_id and uid != uniqueid
        ]

        # Удаляем текущий канал из маппинга
        self._channel_map.pop(uniqueid, None)
        self._channel_names.pop(uniqueid, None)

        if not remaining_channels:
            # Последний канал -- завершаем сессию
            self._sm.end_session(call_id)
            self._linked_map = {
                k: v for k, v in self._linked_map.items() if v != call_id
            }
            self._audiosocket_originated.discard(call_id)
            logger.info(f"AMI: Hangup -- звонок завершён (call_id={call_id[:8]})")
            await self._broadcast_update()
        else:
            logger.debug(
                f"AMI: Hangup одного канала, звонок продолжается "
                f"(call_id={call_id[:8]}, осталось каналов: {len(remaining_channels)})"
            )

    async def _originate_audiosocket(self, call_id: str, channel: str) -> None:
        """AMI Originate: запускаем AudioSocket для real-time STT.

        Архитектура Local-канала:
          ;1 leg -> dialplan [audiosocket-connect] -> AudioSocket(${EXTEN}, 127.0.0.1:9092)
          ;2 leg -> Application=ChanSpy(channel, qS) -> шпионит за аудио звонка

        Аудио от ChanSpy на ;2 проходит через Local bridge к ;1 -> AudioSocket -> TCP.

        UUID передается через имя extension (${EXTEN}) Local-канала,
        т.к. AMI Variable НЕ наследуется на ;1 leg.

        Ключевые флаги:
          /n        -- запрет оптимизации Local-канала (иначе Asterisk уберёт мост)
          q         -- ChanSpy без звукового сигнала (тихий режим)
          S         -- ChanSpy: остановиться при hangup прослушиваемого канала
        """
        try:
            await self._send_action({
                "Action": "Originate",
                "Channel": f"Local/{call_id}@audiosocket-connect/n",
                "Application": "ChanSpy",
                "Data": f"{channel},qS",
                "Async": "true",
                "ActionID": f"audiosocket-{call_id[:8]}",
            })
            logger.info(
                f"AMI: AudioSocket Originate отправлен "
                f"(call_id={call_id[:8]}, channel={channel})"
            )
        except Exception as e:
            logger.error(f"AMI: AudioSocket Originate ошибка: {e}")
            self._audiosocket_originated.discard(call_id)

    async def _broadcast_update(self) -> None:
        """Отправить обновление списка звонков всем дашбордам."""
        try:
            await self._wm.broadcast("calls_update", {
                "active_calls": [s.to_dict() for s in self._sm.active_calls],
                "archived_calls": [s.to_dict() for s in self._sm.archived_calls],
            })
        except Exception as e:
            logger.error(f"AMI: ошибка broadcast: {e}")


# Глобальный экземпляр
ami_client = AsteriskAMIClient(
    sm=session_manager,
    wm=ws_manager,
    host="127.0.0.1",  # AMI всегда на localhost (bindaddr = 127.0.0.1 в manager.conf)
    port=settings.asterisk_ami_port,
    username=settings.asterisk_ami_user,
    secret=settings.asterisk_ami_password,
)
