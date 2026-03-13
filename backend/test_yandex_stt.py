"""Полный тест Yandex SpeechKit: TTS -> STT (speech round-trip).

Генерирует речь через Yandex TTS REST API,
затем отправляет аудио на распознавание через STT gRPC Streaming.

Проверяет полный цикл: текст -> аудио -> текст.

Использование:
    python3 test_yandex_stt.py                   # синтетический тон (базовый тест)
    python3 test_yandex_stt.py --tts              # TTS -> STT (полный цикл)
    python3 test_yandex_stt.py --file test.wav    # из WAV-файла
"""

import argparse
import asyncio
import io
import logging
import math
import os
import struct
import sys
import time
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional

import grpc
import httpx

# Добавляем proto/ в sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "proto"))

from yandex.cloud.ai.stt.v3 import stt_pb2, stt_service_pb2_grpc  # noqa: E402

# Загружаем .env
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SPEECHKIT_STT_ENDPOINT = "stt.api.cloud.yandex.net:443"
SPEECHKIT_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
SAMPLE_RATE = 8000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("stt_test")


# ============================================================
# Источники аудио
# ============================================================


def generate_tone_pcm(
    freq: float = 440.0,
    duration_sec: float = 3.0,
    sample_rate: int = SAMPLE_RATE,
    amplitude: float = 0.5,
) -> bytes:
    """Генерирует PCM LINEAR16 тоновый сигнал."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * freq * t)
        samples.append(int(value * 32767))
    return struct.pack(f"<{len(samples)}h", *samples)


def read_wav_file(filepath: str) -> bytes:
    """Читает WAV-файл и возвращает raw PCM."""
    with wave.open(filepath, "rb") as wf:
        assert wf.getnchannels() == 1, f"Ожидается моно, получено {wf.getnchannels()} каналов"
        assert wf.getsampwidth() == 2, f"Ожидается 16-bit, получено {wf.getsampwidth()*8}-bit"
        rate = wf.getframerate()
        if rate != SAMPLE_RATE:
            logger.warning("WAV sample rate = %d Hz (ожидается %d Hz)", rate, SAMPLE_RATE)
        return wf.readframes(wf.getnframes())


async def synthesize_tts(
    api_key: str,
    folder_id: str,
    text: str,
    voice: str = "filipp",
    speed: float = 1.0,
) -> bytes:
    """Синтез речи через Yandex TTS REST API v1.

    Возвращает raw PCM LINEAR16 8kHz mono.
    """
    logger.info("TTS: Синтезируем: \"%s\" (voice=%s)", text, voice)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            SPEECHKIT_TTS_URL,
            headers={
                "Authorization": f"Api-Key {api_key}",
            },
            data={
                "text": text,
                "lang": "ru-RU",
                "voice": voice,
                "speed": str(speed),
                "format": "lpcm",
                "sampleRateHertz": str(SAMPLE_RATE),
                "folderId": folder_id,
            },
        )

        if response.status_code != 200:
            logger.error("TTS: HTTP %d: %s", response.status_code, response.text[:200])
            raise RuntimeError(f"TTS: HTTP {response.status_code}: {response.text[:200]}")

        pcm_data = response.content
        duration = len(pcm_data) / (SAMPLE_RATE * SAMPLE_WIDTH)
        logger.info("TTS: OK -- %d байт, ~%.1f сек", len(pcm_data), duration)
        return pcm_data


async def synthesize_multiple_phrases(
    api_key: str,
    folder_id: str,
    phrases: list[str],
    voice: str = "filipp",
    pause_sec: float = 1.0,
) -> bytes:
    """Синтезирует несколько фраз с паузами между ними."""
    all_pcm = bytearray()
    pause_samples = int(SAMPLE_RATE * pause_sec) * SAMPLE_WIDTH
    pause_data = b"\x00" * pause_samples

    for i, phrase in enumerate(phrases):
        pcm = await synthesize_tts(api_key, folder_id, phrase, voice)
        all_pcm.extend(pcm)
        if i < len(phrases) - 1:
            all_pcm.extend(pause_data)  # Пауза между фразами

    total_duration = len(all_pcm) / (SAMPLE_RATE * SAMPLE_WIDTH)
    logger.info("TTS: Всего %d байт, ~%.1f сек (%d фраз)", len(all_pcm), total_duration, len(phrases))
    return bytes(all_pcm)


# ============================================================
# STT Streaming
# ============================================================


async def test_stt_streaming(
    api_key: str,
    folder_id: str,
    audio_data: bytes,
    chunk_size: int = 3200,  # 200ms при 8kHz 16-bit mono
    expected_texts: Optional[list[str]] = None,
) -> bool:
    """Запускает streaming recognition и выводит результаты.

    Returns:
        True если тест прошёл успешно.
    """

    logger.info("=" * 60)
    logger.info("Yandex SpeechKit STT v3 -- Streaming Test")
    logger.info("=" * 60)
    logger.info("Endpoint: %s", SPEECHKIT_STT_ENDPOINT)
    logger.info("API Key: %s...%s (%d chars)", api_key[:8], api_key[-4:], len(api_key))
    logger.info("Folder ID: %s", folder_id)
    logger.info("Audio: %d bytes, ~%.1f sec", len(audio_data), len(audio_data) / (SAMPLE_RATE * SAMPLE_WIDTH))
    if expected_texts:
        logger.info("Ожидаемый текст: %s", expected_texts)
    logger.info("-" * 60)

    # Шаг 1: gRPC-канал
    logger.info("[1/4] Создаём gRPC-канал...")
    creds = grpc.ssl_channel_credentials()
    channel = grpc.aio.secure_channel(SPEECHKIT_STT_ENDPOINT, creds)

    try:
        state = channel.get_state(try_to_connect=True)
        deadline = time.time() + 10
        while state != grpc.ChannelConnectivity.READY and time.time() < deadline:
            await asyncio.sleep(0.5)
            state = channel.get_state(try_to_connect=True)

        if state != grpc.ChannelConnectivity.READY:
            logger.error("[!] gRPC канал не готов: state=%s", state)
            return False

        logger.info("[1/4] gRPC канал готов (READY)")
    except Exception as e:
        logger.error("[!] gRPC connection failed: %s", e)
        return False

    # Шаг 2: Stub
    logger.info("[2/4] Создаём RecognizerStub...")
    stub = stt_service_pb2_grpc.RecognizerStub(channel)

    # Шаг 3: Session options
    logger.info("[3/4] Настраиваем streaming session...")

    session_options = stt_pb2.StreamingRequest(
        session_options=stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                model="general",
                audio_format=stt_pb2.AudioFormatOptions(
                    raw_audio=stt_pb2.RawAudio(
                        audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                        sample_rate_hertz=SAMPLE_RATE,
                        audio_channel_count=CHANNELS,
                    )
                ),
                text_normalization=stt_pb2.TextNormalizationOptions(
                    text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                    profanity_filter=False,
                    literature_text=True,
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=["ru-RU"],
                ),
            ),
            eou_classifier=stt_pb2.EouClassifierOptions(
                default_classifier=stt_pb2.DefaultEouClassifier(
                    type=stt_pb2.DefaultEouClassifier.DEFAULT,
                    max_pause_between_words_hint_ms=1500,
                ),
            ),
        )
    )

    results = {"partial": 0, "final": 0, "eou": 0, "errors": 0}
    final_texts: list[str] = []

    async def request_generator():
        yield session_options
        logger.info("[3/4] Session options отправлены")

        offset = 0
        chunk_count = 0
        while offset < len(audio_data):
            chunk = audio_data[offset: offset + chunk_size]
            yield stt_pb2.StreamingRequest(
                chunk=stt_pb2.AudioChunk(data=chunk)
            )
            chunk_count += 1
            offset += chunk_size
            await asyncio.sleep(0.05)

        logger.info("[3/4] Отправлено %d чанков (%d байт)", chunk_count, len(audio_data))

    # Шаг 4: Streaming
    logger.info("[4/4] Запуск RecognizeStreaming...")

    metadata = [("authorization", f"Api-Key {api_key}")]
    if folder_id:
        metadata.append(("x-folder-id", folder_id))

    try:
        start_time = time.time()
        responses = stub.RecognizeStreaming(
            request_generator(),
            metadata=metadata,
        )

        async for response in responses:
            event_type = response.WhichOneof("Event")
            elapsed = time.time() - start_time

            if event_type == "partial":
                results["partial"] += 1
                for alt in response.partial.alternatives:
                    if alt.text:
                        logger.info("  [PARTIAL] t=%.1fs: \"%s\"", elapsed, alt.text[:100])

            elif event_type == "final":
                results["final"] += 1
                for alt in response.final.alternatives:
                    conf = alt.confidence
                    if alt.text:
                        final_texts.append(alt.text)
                        logger.info("  [FINAL] t=%.1fs (%.0f%%): \"%s\"", elapsed, conf * 100, alt.text[:100])

            elif event_type == "final_refinement":
                results["final"] += 1
                for alt in response.final_refinement.normalized_text.alternatives:
                    conf = alt.confidence
                    if alt.text:
                        # Refined text заменяет предыдущий final
                        if final_texts:
                            final_texts[-1] = alt.text
                        else:
                            final_texts.append(alt.text)
                        logger.info("  [REFINED] t=%.1fs (%.0f%%): \"%s\"", elapsed, conf * 100, alt.text[:100])

            elif event_type == "eou_update":
                results["eou"] += 1
                logger.info("  [EOU] t=%.1fs", elapsed)

            elif event_type == "status_code":
                pass  # Тихо пропускаем status updates

            elif event_type == "classifier_update":
                update = response.classifier_update
                name = update.classifier_result.classifier
                for label in update.classifier_result.highlights:
                    logger.info("  [CLASSIFIER] %s = %.1f%%", name, label.value * 100)

        total_time = time.time() - start_time
        logger.info("-" * 60)
        logger.info("Streaming завершён за %.1f сек", total_time)

    except grpc.aio.AioRpcError as e:
        results["errors"] += 1
        logger.error("-" * 60)
        logger.error("[!] gRPC ERROR: %s", e.code())
        logger.error("    Details: %s", e.details())

        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            logger.error("    --> API-ключ невалиден или истёк!")
        elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
            logger.error("    --> Нет доступа. Проверьте folder_id")

    except Exception as e:
        results["errors"] += 1
        logger.error("[!] Unexpected error: %s: %s", type(e).__name__, e)

    finally:
        await channel.close()

    # Итоговая сводка
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ:")
    logger.info("  Partial results:  %d", results["partial"])
    logger.info("  Final results:    %d", results["final"])
    logger.info("  EOU events:       %d", results["eou"])
    logger.info("  Errors:           %d", results["errors"])

    if final_texts:
        logger.info("  Распознанный текст:")
        for i, text in enumerate(final_texts, 1):
            logger.info("    %d. \"%s\"", i, text)

    # Проверка ожидаемых текстов
    success = True
    if results["errors"] > 0:
        logger.error("  STATUS: FAIL -- есть ошибки!")
        success = False
    elif expected_texts and final_texts:
        recognized = " ".join(final_texts).lower()
        all_found = True
        for expected in expected_texts:
            # Проверяем, что ключевые слова из ожидаемого текста присутствуют
            keywords = [w for w in expected.lower().split() if len(w) > 3]
            found = sum(1 for kw in keywords if kw in recognized)
            ratio = found / len(keywords) if keywords else 0
            if ratio >= 0.5:
                logger.info("  [v] Фраза найдена (%.0f%%): \"%s\"", ratio * 100, expected)
            else:
                logger.warning("  [x] Фраза НЕ найдена (%.0f%%): \"%s\"", ratio * 100, expected)
                all_found = False
        if all_found:
            logger.info("  STATUS: OK -- TTS->STT цикл успешен!")
        else:
            logger.warning("  STATUS: PARTIAL -- некоторые фразы не распознаны")
            success = False
    elif results["final"] > 0 or results["partial"] > 0:
        logger.info("  STATUS: OK -- STT работает")
    else:
        logger.warning("  STATUS: WARNING -- нет результатов")
        success = False

    logger.info("=" * 60)
    return success


# ============================================================
# Main
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Тест Yandex SpeechKit STT v3 + TTS")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=str, help="Путь к WAV-файлу (моно, 16-bit, 8kHz)")
    source.add_argument("--tts", action="store_true", help="Синтезировать речь через TTS и отправить на STT")
    parser.add_argument("--duration", type=float, default=3.0, help="Длительность тона (сек)")
    parser.add_argument("--api-key", type=str, help="Yandex API Key (или YANDEX_API_KEY из .env)")
    parser.add_argument("--folder-id", type=str, help="Yandex Folder ID (или YANDEX_FOLDER_ID из .env)")
    parser.add_argument("--voice", type=str, default="filipp", help="TTS voice (default: filipp)")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("YANDEX_API_KEY", "")
    folder_id = args.folder_id or os.environ.get("YANDEX_FOLDER_ID", "")

    if not api_key:
        logger.error("YANDEX_API_KEY не задан! Используйте --api-key или .env")
        sys.exit(1)
    if not folder_id:
        logger.error("YANDEX_FOLDER_ID не задан! Используйте --folder-id или .env")
        sys.exit(1)

    asyncio.run(_async_main(args, api_key, folder_id))


async def _async_main(args, api_key: str, folder_id: str):
    expected_texts = None

    if args.tts:
        # TTS -> STT полный цикл
        phrases = [
            "Здравствуйте, меня зовут Алексей.",
            "Я хотел бы обсудить условия сотрудничества.",
        ]
        logger.info("=" * 60)
        logger.info("Режим: TTS -> STT (полный цикл)")
        logger.info("Фразы для синтеза:")
        for i, p in enumerate(phrases, 1):
            logger.info("  %d. \"%s\"", i, p)
        logger.info("=" * 60)

        audio_data = await synthesize_multiple_phrases(
            api_key, folder_id, phrases, voice=args.voice
        )
        expected_texts = phrases

    elif args.file:
        logger.info("Источник аудио: WAV-файл %s", args.file)
        audio_data = read_wav_file(args.file)

    else:
        logger.info("Источник аудио: синтетический тон (440 Hz, %.1f сек)", args.duration)
        audio_data = generate_tone_pcm(duration_sec=args.duration)

    success = await test_stt_streaming(
        api_key, folder_id, audio_data, expected_texts=expected_texts
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
