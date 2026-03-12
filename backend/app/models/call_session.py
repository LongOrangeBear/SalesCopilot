"""CallSession -- in-memory объект звонка и менеджер сессий."""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CallDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    RINGING = "ringing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    ENDED = "ended"


class Speaker(str, Enum):
    CLIENT = "client"
    MANAGER = "manager"


@dataclass
class Utterance:
    """Одна реплика в диалоге."""
    speaker: Speaker
    text: str
    timestamp: float
    is_final: bool = True
    confidence: float = 1.0


@dataclass
class AIRequest:
    """Запрос к LLM."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prompt: str = ""
    context: str = ""
    model: str = ""
    sent_at: float = 0.0
    response: str = ""
    received_at: float = 0.0
    duration_ms: float = 0.0


@dataclass
class PipelineTimings:
    """Задержки каждого этапа пайплайна."""
    audio_transfer_ms: float = 0.0
    stt_ms: float = 0.0
    llm_ms: float = 0.0
    delivery_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class CRMContext:
    """Данные клиента из CRM."""
    contact_name: str = ""
    company: str = ""
    deal_stage: str = ""
    deal_budget: str = ""
    phone: str = ""
    notes: str = ""


@dataclass
class CallSession:
    """Сессия одного звонка -- все данные об активном или завершённом звонке."""

    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    direction: CallDirection = CallDirection.INBOUND
    status: CallStatus = CallStatus.RINGING

    # Участники
    caller_number: str = ""
    caller_name: str = ""
    callee_number: str = ""
    callee_name: str = ""
    manager_extension: str = ""

    # Временные метки
    started_at: float = field(default_factory=time.time)
    answered_at: Optional[float] = None
    ended_at: Optional[float] = None

    # Транскрипт
    transcript: list[Utterance] = field(default_factory=list)
    current_speaker: Optional[Speaker] = None

    # Контекст CRM
    crm_context: CRMContext = field(default_factory=CRMContext)

    # ИИ
    ai_requests: list[AIRequest] = field(default_factory=list)
    ai_hints: list[str] = field(default_factory=list)

    # Тайминги
    pipeline_timings: list[PipelineTimings] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        end = self.ended_at or time.time()
        start = self.answered_at or self.started_at
        return round(end - start, 1)

    def to_dict(self) -> dict:
        """Сериализация для API."""
        return {
            "call_id": self.call_id,
            "direction": self.direction.value,
            "status": self.status.value,
            "caller_number": self.caller_number,
            "caller_name": self.caller_name,
            "callee_number": self.callee_number,
            "callee_name": self.callee_name,
            "manager_extension": self.manager_extension,
            "started_at": self.started_at,
            "answered_at": self.answered_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "current_speaker": self.current_speaker.value if self.current_speaker else None,
            "transcript": [
                {
                    "speaker": u.speaker.value,
                    "text": u.text,
                    "timestamp": u.timestamp,
                    "is_final": u.is_final,
                    "confidence": u.confidence,
                }
                for u in self.transcript
            ],
            "crm_context": {
                "contact_name": self.crm_context.contact_name,
                "company": self.crm_context.company,
                "deal_stage": self.crm_context.deal_stage,
                "deal_budget": self.crm_context.deal_budget,
                "phone": self.crm_context.phone,
            },
            "ai_requests": [
                {
                    "request_id": r.request_id,
                    "prompt": r.prompt,
                    "context": r.context,
                    "model": r.model,
                    "sent_at": r.sent_at,
                    "response": r.response,
                    "received_at": r.received_at,
                    "duration_ms": r.duration_ms,
                }
                for r in self.ai_requests
            ],
            "ai_hints": self.ai_hints,
            "pipeline_timings": [
                {
                    "audio_transfer_ms": t.audio_transfer_ms,
                    "stt_ms": t.stt_ms,
                    "llm_ms": t.llm_ms,
                    "delivery_ms": t.delivery_ms,
                    "total_ms": t.total_ms,
                }
                for t in self.pipeline_timings
            ],
        }


class SessionManager:
    """Реестр активных и завершённых сессий."""

    def __init__(self):
        self._active: dict[str, CallSession] = {}
        self._archive: list[CallSession] = []

    def create_session(self, **kwargs) -> CallSession:
        session = CallSession(**kwargs)
        self._active[session.call_id] = session
        return session

    def get_session(self, call_id: str) -> Optional[CallSession]:
        return self._active.get(call_id) or next(
            (s for s in self._archive if s.call_id == call_id), None
        )

    def end_session(self, call_id: str) -> Optional[CallSession]:
        session = self._active.pop(call_id, None)
        if session:
            session.status = CallStatus.ENDED
            session.ended_at = time.time()
            self._archive.append(session)
        return session

    @property
    def active_calls(self) -> list[CallSession]:
        return list(self._active.values())

    @property
    def archived_calls(self) -> list[CallSession]:
        return list(self._archive)

    @property
    def active_count(self) -> int:
        return len(self._active)


# Глобальный экземпляр
session_manager = SessionManager()
