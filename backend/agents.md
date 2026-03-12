# Backend -- архитектурные правила

## Структура проекта

```
backend/
  main.py                  # Точка входа (тонкий entrypoint)
  config.py                # Pydantic Settings (.env)
  requirements.txt         # Зависимости
  app/                     # Основной пакет приложения
    __init__.py             #   create_app() -- фабрика FastAPI
    routes/                 #   HTTP/WS роуты
      __init__.py           #     Реэкспорт роутеров
      health.py             #     /api/health, /api/check-keys, /api/system
      calls.py              #     /api/calls, /api/calls/{id}
      ws.py                 #     /ws/dashboard
    services/               #   Бизнес-логика, интеграции с внешними API
      __init__.py
      stt.py                #     Yandex SpeechKit STT клиент
      llm.py                #     OpenAI LLM клиент
    models/                 #   Доменные модели (dataclasses)
      __init__.py
      call_session.py       #     CallSession, Utterance, SessionManager
    core/                   #   Инфраструктура
      __init__.py
      ws_manager.py         #     DashboardConnectionManager
      dependencies.py       #     FastAPI Depends() -- DI
    demo/                   #   Тестовые данные
      __init__.py
      fixtures.py           #     create_demo_session()
```

## Правила размещения нового кода

### Новый API-эндпоинт
1. Создать или дополнить файл в `app/routes/`
2. Использовать `APIRouter` с prefix и tags
3. Зависимости получать через `Depends()` из `app/core/dependencies.py`
4. Подключить роутер в `app/routes/__init__.py` и `app/__init__.py`

### Новая интеграция (CRM, Asterisk ARI, etc.)
1. Создать файл в `app/services/` (например `app/services/crm.py`)
2. Класс-клиент с методами + глобальный экземпляр
3. Добавить DI-функцию в `app/core/dependencies.py`
4. Зарегистрировать shutdown в lifespan (`app/__init__.py`)

### Новая доменная модель
1. Создать или дополнить файл в `app/models/`
2. Использовать `@dataclass` (или Pydantic `BaseModel` для API-схем)
3. Реэкспортировать в `app/models/__init__.py`

### Новая конфигурация
1. Добавить поле в `config.py` -> `Settings`
2. Добавить переменную в `.env`
3. Обновить `credentials.md` в корне проекта

## Чеклист перед коммитом

- [ ] `source venv/bin/activate && python3 -c "from app import create_app; print('OK')"` -- проходит
- [ ] Новые роуты используют `Depends()` (не импортируют глобальные синглтоны напрямую)
- [ ] Нет `import` внутри функций (кроме условных зависимостей)
- [ ] Ответы API имеют корректные HTTP-коды (`HTTPException` для ошибок)
- [ ] CORS ограничен (не `allow_origins=["*"]` в production)
- [ ] Нет дублирования логики (вынесена в services/)
- [ ] Комментарии и логи на русском (кириллица, без транслитерации)

## Запрещено

- Писать бизнес-логику в `main.py` -- это только entrypoint
- Использовать `return {}, 404` -- использовать `HTTPException`
- Создавать `httpx.AsyncClient` внутри каждого запроса -- использовать shared клиент
- Хранить секреты в коде -- только через `.env` и `config.py`

## Частые ошибки (из ревью)

Этот раздел основан на реальных ошибках, найденных при аудите. Проверяй эти пункты перед коммитом.

### 1. Дубликаты файлов вне `app/`
Не хранить `.py` файлы с бизнес-логикой в корне `backend/`. Всё должно быть внутри `app/` (routes, services, models, core). Файлы в корне: только `main.py`, `config.py`, `requirements.txt`.

### 2. Прямой импорт синглтонов в роутах
**Неправильно:** `from app.services.stt import stt_client` в роуте.
**Правильно:** `stt=Depends(get_stt_client)` в сигнатуре эндпоинта.
Каждый новый сервис должен иметь DI-функцию в `app/core/dependencies.py`.

### 3. Забыть закрыть клиент в lifespan
Каждый сервис с persistent-соединением (httpx, gRPC, WebSocket) должен быть зарегистрирован в `lifespan()` (`app/__init__.py`) для корректного shutdown.

### 4. JSON от клиента без валидации
В WebSocket-хендлерах оборачивать `json.loads()` в `try/except json.JSONDecodeError`. Невалидный JSON от клиента не должен крашить сервер.

### 5. Логирование ошибок без traceback
В `except` блоках использовать `traceback.format_exc()` для полного стека, а не просто `str(e)`.

