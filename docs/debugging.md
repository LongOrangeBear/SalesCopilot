# Руководство по отладке и логгированию SalesCopilot

Эта документация исчерпывающе описывает, как и где искать логи для диагностики любых проблем в цепочке:
**Asterisk (Звонки / AudioSocket) -> Backend (FastAPI / STT / WS) -> Frontend (Dashboard)**.

---

## 1. Backend Service (FastAPI / Uvicorn)

Здесь находится 90% бизнес-логики: интеграция с Yandex STT, AMI-клиент для управления Asterisk, AudioSocket TCP-сервер, WebSocket-отправка событий на дашборд.

**Как смотреть (production на VPS):**
```bash
# Текущие логи в реальном времени
journalctl -u salescopilot-backend -f

# Логи за последний час
journalctl -u salescopilot-backend --since "1 hour ago"

# Найти все ошибки STT без постраничного режима
journalctl -u salescopilot-backend --no-pager | grep -i "STT"
```

**Что искать в этих логах:**
- `AMI: ...` — события коннекта к Asterisk Manager Interface, ошибки авторизации.
- `AudioSocket: ...` — ошибки парсинга входящих TCP фреймов, обрывы стримов аудио.
- `STT: ...` — ошибки gRPC соединения с Yandex SpeechKit, неверный API-ключ, "CallSession не найдена".
- Ошибки Python (`Traceback (most recent call last)`), которые "тихо" падали в консоль.

---

## 2. Asterisk PBX (Движок звонков)

Asterisk отвечает за SIP-подключения (софтфоны) и запуск AudioSocket с аудиоданными. Если Backend вообще не получает аудио, значит проблема на стороне Asterisk.

**Как смотреть (production на VPS):**
```bash
# 1. Основной лог-файл (включает NOTICE, WARNING, ERROR, DEBUG)
tail -f /var/log/asterisk/messages.log

# Искать конкретные ошибки AudioSocket (например, почему не подключился):
grep -i audiosocket /var/log/asterisk/messages.log

# Искать ошибки SIP-регистраций (пароли, порты):
grep -i pjsip /var/log/asterisk/messages.log | grep -i fail

# 2. Интерактивная консоль Asterisk (CLI)
asterisk -rvvvvv
```

**Работа в консоли Asterisk CLI (`asterisk -rvvvvv`):**
- **Посмотреть живой поток (Call trace):** Сделайте тестовый звонок, и в консоли побегут цветные строчки (Dialplan execution). Смотрите на строки, начинающиеся с `app_audiosocket.c`.
- **Включить дебаг AMI:** `manager show connected` (посмотреть, висит ли сессия Backend'а).
- **Сбросить SIP-подключения:** `pjsip show endpoints` (посмотреть статусы софтфонов).

---

## 3. Frontend Dashboard и Nginx

Если Backend и Asterisk работают (STT распознается в консоли), но интерфейс не отображает Pipeline Logs:

**Как ловить ошибки на стороне фронтенда:**
1. Открыть **DevTools (F12) -> Console**. Проверить, нет ли CORS ошибок или обрывов WebSocket (`ws://` disconnection).
2. Зайти во вкладку **Network -> WS**. Проверить, какие JSON-пакеты летят с сервера.

**Логи Nginx (если дашборд вообще не грузится):**
```bash
# Ошибки (502 Bad Gateway - скорее всего упал backend)
tail -f /var/log/nginx/error.log

# Доступ (CORS / HTTP запросы)
tail -f /var/log/nginx/access.log
```

---

## 4. Памятка: Локализация проблемы по цепочке (Pipeline Flow)

Обычно сигнал идет так:
1. `Softphone` звонит на номер -> (Смотрим **Asterisk messages.log**)
2. `Asterisk` поднимает трубку и создает событие AMI (`BridgeEnter`) -> (Смотрим **journalctl -u salescopilot-backend** -> `AMI: ...`)
3. `Backend` ловит событие AMI и делает AMI Originate (создает Local-канал), чтобы запустить ChanSpy и направить его в AudioSocket. -> (Смотрим **journalctl -u salescopilot-backend** -> `AMI Originate...`)
4. `Asterisk` запускает приложение `AudioSocket(${UUID})`. Если UUID не передался или TCP порт закрыт — соединение рвется мгновенно. -> (Смотрим **Asterisk messages.log** -> `ERROR app_audiosocket.c`)
5. `Backend` принимает байты из TCP:9092, собирает WAV-шары (chunks) и шлет в Yandex STT. -> (Смотрим **Backend journalctl**).
6. От Yandex возвращается текст. `Backend` шлет его по WebSocket в браузер. -> (Смотрим **Browser F12 / Консоль**).

Если на любом из этих 6 шагов лога нет — мы нашли виновника, смотрим его логи.
