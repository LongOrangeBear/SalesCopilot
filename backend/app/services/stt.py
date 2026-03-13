"""Yandex SpeechKit STT -- gRPC Streaming API v3.

Bidirectional streaming клиент для real-time распознавания речи.
Поддерживает:
- Streaming recognition с partial и final results
- Классификаторы (приветствие, прощание, негатив, мат, автоответчик)
- Аналитику речи (скорость, паузы, перебивания)
- Нормализацию текста (числа, даты, пунктуация)
- EOU (End-of-Utterance) детекцию
- Ротацию сессии каждые 4.5 мин (лимит 5 мин)
"""

import asyncio
import logging
import sys
import time
from typing import AsyncGenerator, Callable, Optional

import grpc

from config import settings

# Добавляем proto/ в sys.path для импорта сгенерированных stubs
sys.path.insert(0, str(settings.BASE_DIR / "proto"))

from yandex.cloud.ai.stt.v3 import stt_pb2, stt_service_pb2_grpc  # noqa: E402

logger = logging.getLogger(__name__)

# Yandex SpeechKit gRPC endpoint
SPEECHKIT_ENDPOINT = "stt.api.cloud.yandex.net:443"

# Лимит сессии -- 5 мин, ротация на 4.5 мин
SESSION_ROTATION_SEC = 270  # 4.5 мин


class SpeechKitSTTClient:
    """gRPC streaming STT клиент для Yandex SpeechKit API v3."""

    def __init__(self) -> None:
        self._api_key: str = settings.yandex_api_key
        self._folder_id: str = settings.yandex_folder_id
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[stt_service_pb2_grpc.RecognizerStub] = None

    async def _ensure_channel(self) -> None:
        """Создать или переиспользовать gRPC-канал."""
        if self._channel is None:
            creds = grpc.ssl_channel_credentials()
            self._channel = grpc.aio.secure_channel(SPEECHKIT_ENDPOINT, creds)
            self._stub = stt_service_pb2_grpc.RecognizerStub(self._channel)
            logger.info("STT: gRPC канал создан")

    def _build_session_options(self) -> stt_pb2.StreamingRequest:
        """Формирование настроек сессии распознавания."""
        return stt_pb2.StreamingRequest(
            session_options=stt_pb2.StreamingOptions(
                recognition_model=stt_pb2.RecognitionModelOptions(
                    model="general",
                    language_code="ru-RU",
                    audio_format=stt_pb2.AudioFormatOptions(
                        raw_audio=stt_pb2.RawAudio(
                            audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                            sample_rate_hertz=8000,
                            audio_channel_count=1,
                        )
                    ),
                    text_normalization=stt_pb2.TextNormalizationOptions(
                        text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                        profanity_filter=True,
                        literature_text=True,
                    ),
                ),
                # Классификаторы для sales copilot
                recognition_classifier=stt_pb2.RecognitionClassifierOptions(
                    classifiers=[
                        stt_pb2.RecognitionClassifier(
                            classifier="formal_greeting",
                            triggers=[stt_pb2.RecognitionClassifier.ON_UTTERANCE],
                        ),
                        stt_pb2.RecognitionClassifier(
                            classifier="informal_greeting",
                            triggers=[stt_pb2.RecognitionClassifier.ON_UTTERANCE],
                        ),
                        stt_pb2.RecognitionClassifier(
                            classifier="formal_farewell",
                            triggers=[stt_pb2.RecognitionClassifier.ON_UTTERANCE],
                        ),
                        stt_pb2.RecognitionClassifier(
                            classifier="negative",
                            triggers=[stt_pb2.RecognitionClassifier.ON_UTTERANCE],
                        ),
                        stt_pb2.RecognitionClassifier(
                            classifier="answerphone",
                            triggers=[stt_pb2.RecognitionClassifier.ON_UTTERANCE],
                        ),
                    ]
                ),
                # Аналитика речи
                speech_analysis=stt_pb2.SpeechAnalysisOptions(
                    enable_speaker_analysis=True,
                    enable_conversation_analysis=True,
                    descriptive_statistics_quantiles=[0.5, 0.9],
                ),
                # EOU -- баланс скорости и точности
                eou_classifier_options=stt_pb2.EouClassifierOptions(
                    default_classifier=stt_pb2.DefaultEouClassifier(
                        type=stt_pb2.DefaultEouClassifier.DEFAULT,
                        max_pause_between_words_hint_ms=800,
                    ),
                ),
            )
        )

    async def recognize_streaming(
        self,
        audio_generator: AsyncGenerator[bytes, None],
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str, float], None]] = None,
        on_classifier: Optional[Callable[[str, float], None]] = None,
        on_eou: Optional[Callable[[], None]] = None,
    ) -> None:
        """Запуск bidirectional streaming распознавания.

        Args:
            audio_generator: Async-генератор аудио-чанков (LINEAR16_PCM, 8kHz, mono)
            on_partial: Callback для промежуточных результатов (text)
            on_final: Callback для финальных результатов (text, confidence)
            on_classifier: Callback для классификаторов (classifier_name, probability)
            on_eou: Callback для End-of-Utterance
        """
        await self._ensure_channel()

        session_start = time.time()

        async def request_generator():
            # Первое сообщение -- настройки сессии
            yield self._build_session_options()

            # Далее -- аудио-чанки
            async for chunk in audio_generator:
                # Проверка ротации сессии
                elapsed = time.time() - session_start
                if elapsed >= SESSION_ROTATION_SEC:
                    logger.info("STT: ротация сессии (%.0f сек)", elapsed)
                    return

                yield stt_pb2.StreamingRequest(
                    chunk=stt_pb2.AudioChunk(data=chunk)
                )

        metadata = [("authorization", f"Api-Key {self._api_key}")]
        if self._folder_id:
            metadata.append(("x-folder-id", self._folder_id))

        try:
            responses = self._stub.RecognizeStreaming(
                request_generator(),
                metadata=metadata,
            )

            async for response in responses:
                self._process_response(response, on_partial, on_final, on_classifier, on_eou)

        except grpc.aio.AioRpcError as e:
            logger.error("STT gRPC: %s (code=%s)", e.details(), e.code())
            raise
        except Exception as e:
            logger.error("STT: %s", e)
            raise

    def _process_response(
        self,
        response: stt_pb2.StreamingResponse,
        on_partial: Optional[Callable],
        on_final: Optional[Callable],
        on_classifier: Optional[Callable],
        on_eou: Optional[Callable],
    ) -> None:
        """Обработка ответа от SpeechKit."""
        event_type = response.WhichOneof("Event")

        if event_type == "partial" and on_partial:
            for alt in response.partial.alternatives:
                on_partial(alt.text)

        elif event_type == "final" and on_final:
            for alt in response.final.alternatives:
                confidence = alt.confidence if alt.HasField("confidence") else 0.0
                on_final(alt.text, confidence)

        elif event_type == "final_refinement" and on_final:
            # Нормализованные окончательные результаты
            for alt in response.final_refinement.normalized_text.alternatives:
                confidence = alt.confidence if alt.HasField("confidence") else 0.0
                on_final(alt.text, confidence)

        elif event_type == "eou_update" and on_eou:
            on_eou()

        elif event_type == "classifier_update" and on_classifier:
            update = response.classifier_update
            classifier_name = update.classifier_result.classifier
            for label in update.classifier_result.highlights:
                on_classifier(classifier_name, label.value)

        elif event_type == "speaker_analysis":
            # Аналитика по говорящему -- логируем
            logger.debug("STT speaker_analysis: %s", response.speaker_analysis)

        elif event_type == "conversation_analysis":
            # Аналитика по диалогу -- логируем
            logger.debug("STT conversation_analysis: %s", response.conversation_analysis)

    async def check_connection(self) -> bool:
        """Проверка доступности gRPC-канала."""
        try:
            await self._ensure_channel()
            # Пробуем создать канал и проверить connectivity
            state = self._channel.get_state(try_to_connect=True)
            logger.info("STT: gRPC state = %s", state)
            return True
        except Exception as e:
            logger.error("STT: check_connection failed: %s", e)
            return False

    async def close(self) -> None:
        """Закрытие gRPC-канала."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.info("STT: gRPC канал закрыт")


# Синглтон
stt_client = SpeechKitSTTClient()
