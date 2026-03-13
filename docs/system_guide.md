# SalesCopilot — Архитектура и Руководство по запуску

Документация описывает текущую архитектуру, структуру проекта и инструкции по локальному запуску и перезапуску всех компонентов приложения.

---

## 1. Архитектура системы

Система состоит из трёх основных блоков:
1. **Телефония (Asterisk на VPS):** Принимает входящие звонки от SIP-провайдера (Mango), передаёт аудиопотоки на бэкенд через **AudioSocket** (TCP, порт 9092) для real-time STT, записывает звонки через MixMonitor.
2. **Бэкенд (FastAPI):** Ядро бизнес-логики. Принимает аудиопотоки через AudioSocket, отправляет их в **Yandex SpeechKit** (gRPC API v3) для потокового распознавания речи с классификаторами и аналитикой, анализирует текст через **OpenAI (LLM)** и формирует подсказки для менеджера. Управляет in-memory `CallSession` объектами и раздает обновления клиентам по WebSocket (каждую 1 сек).
3. **Админ-дашборд (React/TS):** Live-мониторинг звонков: чат-визуализация транскрипта, тайминги пайплайна, данные CRM, пульсирующая иконка активного звонка, live-таймер.

### Поток данных (Data Flow)
```text
[SIP Провайдер] ---> [Asterisk PBX] ---> [Менеджер (Softphone)]
                           |
                    (AudioSocket TCP)
                           v
                    [FastAPI Backend] <---> [Yandex SpeechKit gRPC STT]
                           |          <---> [OpenAI LLM]
                           |          <---> [Bitrix24 CRM]
                     (WebSocket 1s)
                           v
                   [React Dashboard]
```

---

## 2. Структура проекта

Кодовая база разделена на две основные директории в `/home/meow/work/SalesCopilot`:

### `backend/` (Python/FastAPI)
- `main.py` -- Точка входа.
- `config.py` -- Настройки из `.env` (Pydantic). Включает `BASE_DIR`, `audiosocket_port`.
- `app/models/call_session.py` -- `CallSession` + `SessionManager` (in-memory).
- `app/services/stt.py` -- gRPC streaming STT клиент (Yandex SpeechKit API v3) с классификаторами, speech analysis, EOU.
- `app/services/audiosocket.py` -- TCP-сервер AudioSocket для приёма аудио из Asterisk (порт 9092).
- `app/services/ami.py` -- AMI-клиент для отслеживания звонков Asterisk.
- `proto/` -- gRPC proto-stubs (сгенерированы из `yandex-cloud/cloudapi`).
- `requirements.txt` -- Python-зависимости (`grpcio>=1.71`, `protobuf>=5.29`).
- `.env` -- (Git-ignored) API-ключи и секреты.

### `dashboard/` (React/Vite)
- `src/App.tsx` — Главный UI: список звонков, транскрипт, параметры CallSession, тайминги пайплайна, чеклист сервисов.
- `src/hooks/useWebSocket.ts` — Хук для соединения с бэкендом (с авто-переподключением).
- `src/types.ts` — TypeScript типы (отражают модели бэкенда).
- `src/index.css` — Стили Tailwind с CSS переменными shadcn/ui.
- `tailwind.config.js` — Конфигурация Tailwind.

### `docs/` (Документация)
- `asterisk_deploy.md` — Инструкция по деплою и настройке Asterisk на VPS.
- `system_guide.md` — Этот документ (Архитектура и запуск).

---

## 3. Требования окружения

1. **Python 3.10+** (для бэкенда)
2. **Node.js 18+** и **npm** (для дашборда)
3. Доступ в интернет (Yandex Cloud, OpenAI APi)

---

## 4. Инструкция по запуску

### 4.1. Бэкенд (FastAPI)

1. Перейдите в директорию бэкенда:
   ```bash
   cd /home/meow/work/SalesCopilot/backend
   ```
2. Активируйте виртуальное окружение:
   ```bash
   source venv/bin/activate
   ```
   *(Если зависимости изменились, установите их: `pip install -r requirements.txt`)*
3. Проверьте валидность API-ключей (опционально):
   ```bash
   python test_api_keys.py
   ```
4. Запустите сервер (Uvicorn):
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
   > **Примечание:** Для разработки можно добавить флаг `--reload`, однако если он приводит к мгновенному падению (связано с watched files в Linux), запускайте без него.

Бэкенд будет доступен по адресу: `http://localhost:8000`

### 4.2. Админ-дашборд (React)

1. Перейдите в директорию дашборда:
   ```bash
   cd /home/meow/work/SalesCopilot/dashboard
   ```
2. Установите зависимости (если ещё не установлены):
   ```bash
   npm install
   ```
3. Запустите dev-сервер Vite (на всех интерфейсах):
   ```bash
   npm run dev -- --host
   ```

Дашборд будет доступен по адресу: `http://localhost:5173`

### 4.3. Порты (Development vs Production)

| Сервис | Локально (dev) | Production (VPS) |
|---|---|---|
| Backend (uvicorn) | 8000 | 8211 |
| Dashboard (Vite / nginx) | 5173 | 3211 |
| AudioSocket (STT) | 9092 | 9092 |
| Asterisk SIP | - | 5060 |
| Asterisk AMI | - | 5038 |

> **Примечание:** На продакшене используются нестандартные порты (8211, 3211), чтобы не конфликтовать с другими сервисами на VPS. Порт задаётся в systemd unit (`/etc/systemd/system/salescopilot-backend.service`) и в production `.env` (`PORT=8211`). Nginx слушает на порту 3211 и проксирует `/api/` и `/ws/` на backend (8211).

---

## 5. Перезапуск компонентов

### Перезапуск Бэкенда
Если вы изменили Python-код и сервер запущен без флага `--reload`:
1. Нажмите `Ctrl+C` в терминале с `uvicorn`.
2. Запустите команду повторно:
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Перезапуск Дашборда
Vite сервер поддерживает Hot Module Replacement (HMR) — изменения в `.tsx` / `.css` файлах отображаются в браузере автоматически.
Если сервер завис или падает:
1. Нажмите `Ctrl+C` в терминале с `npm run dev`.
2. Запустите снова: `npm run dev -- --host`.

### Полный перезапуск среды через один скрипт (опционально)
Для удобства в будущем можно создать `start.sh` в корне проекта со следующим содержимым (запустит оба процесса параллельно):

```bash
#!/bin/bash
# Запуск бэкенда в фоне
(cd backend && source venv/bin/activate && python -m uvicorn main:app --host 0.0.0.0 --port 8000) &
BG_PID=$!

# Запуск фронтенда
(cd dashboard && npm run dev -- --host)

# При закрытии убить фоновый процесс
trap "kill $BG_PID" EXIT
```

---

## 6. Что дальше

Аудиопоток из Asterisk передаётся через AudioSocket -> STT -> транскрипт -> дашборд.

Осталось:
1. Подключить SIP-транк (Mango Office) к Asterisk
2. Добавить AMI Originate для автоматического запуска AudioSocket при BridgeEnter
3. Реализовать подсказки ИИ на основе транскрипта + классификаторов SpeechKit
