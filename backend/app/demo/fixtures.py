"""Демо-данные для тестирования дашборда."""

import time

from app.models.call_session import (
    CallSession,
    CallDirection,
    CallStatus,
    Speaker,
    Utterance,
    AIRequest,
    PipelineTimings,
    CRMContext,
    session_manager,
)


def create_demo_session() -> CallSession:
    """Создаёт демо-сессию для тестирования дашборда."""
    session = session_manager.create_session(
        direction=CallDirection.INBOUND,
        caller_number="+7 (495) 123-45-67",
        caller_name="Быстров Алексей",
        callee_number="100",
        callee_name="Менеджер Иванов",
        manager_extension="100",
    )
    session.status = CallStatus.ACTIVE
    session.answered_at = time.time() - 45

    session.crm_context = CRMContext(
        contact_name="Быстров Алексей Петрович",
        company='ООО "ТехноПлюс"',
        deal_stage="Переговоры",
        deal_budget="450 000 руб.",
        phone="+7 (495) 123-45-67",
        notes="Интересовались интеграцией с 1С",
    )

    now = time.time()
    session.transcript = [
        Utterance(Speaker.CLIENT, "Здравствуйте, я звоню по поводу вашего предложения.", now - 40, True, 0.95),
        Utterance(Speaker.MANAGER, "Добрый день, Алексей! Рад вас слышать. Какое именно предложение вас заинтересовало?", now - 35, True, 0.92),
        Utterance(Speaker.CLIENT, "Нам нужна интеграция с нашей 1С-системой. Сколько это будет стоить?", now - 25, True, 0.97),
        Utterance(Speaker.MANAGER, "Конечно, интеграция с 1С -- это один из наших популярных модулей.", now - 18, True, 0.91),
        Utterance(Speaker.CLIENT, "Это слишком дорого для нас. Мы смотрели у конкурентов дешевле.", now - 8, True, 0.98),
    ]
    session.current_speaker = Speaker.CLIENT

    session.ai_requests = [
        AIRequest(
            prompt="Клиент говорит 'дорого' и сравнивает с конкурентами. Предложи ответ.",
            context="Детали сделки: 450к, интеграция 1С, стадия переговоры",
            model="gpt-4o-mini",
            sent_at=now - 7,
            response="Понимаю вашу обеспокоенность ценой. Давайте разберём, что входит в нашу интеграцию -- у нас полный цикл поддержки. Какой бюджет вы закладывали?",
            received_at=now - 5.5,
            duration_ms=1500,
        )
    ]

    session.pipeline_timings = [
        PipelineTimings(
            audio_transfer_ms=45,
            stt_ms=820,
            llm_ms=1500,
            delivery_ms=35,
            total_ms=2400,
        )
    ]

    session.ai_hints = [
        "Клиент сравнивает с конкурентами -- указать на преимущества (полный цикл поддержки, интеграция 1С).",
    ]

    return session
