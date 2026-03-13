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

### `dashboard/` (React/Vite, FSD-архитектура)
- `src/app/App.tsx` -- Главный UI: роутинг по табам (монитор, чеклист, настройки).
- `src/app/index.css` -- Стили Tailwind с CSS переменными shadcn/ui.
- `src/pages/` -- Страницы: monitor, checklist, settings.
- `src/features/` -- Фичи: system-check и др.
- `src/entities/call/` -- Entity звонков с компонентами.
- `src/shared/api/` -- API-клиент и WebSocket-конфигурация.
- `src/shared/types/` -- TypeScript типы.
- `src/shared/ui/` -- UI-компоненты.
- `tailwind.config.js` -- Конфигурация Tailwind.

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
   curl http://localhost:8000/api/check-keys
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

## 6. CI/CD: Деплой на VPS

### 6.1. Пайплайн

Деплой автоматический -- push в `main` запускает GitHub Actions:

```text
git push origin main
       |
       v
[GitHub Actions]  -->  SSH на VPS  -->  deploy.sh
       |                                    |
       v                                    v
[Verify step]                        git pull
  - systemctl is-active              pip install -r requirements.txt
  - curl /api/health                 npm ci && npm run build
  - cat version.json                 systemctl restart backend
                                     systemctl reload nginx
```

### 6.2. Файлы деплоя

| Файл | Где | Назначение |
|---|---|---|
| `.github/workflows/deploy.yml` | Репозиторий | GitHub Actions workflow |
| `deploy.sh` | Репозиторий (корень) | Скрипт деплоя, выполняется на VPS |
| `dashboard/.env.production` | Репозиторий | Vite env для production-сборки |

### 6.3. GitHub Secrets

Настроены в Settings -> Secrets and variables -> Actions:

| Secret | Описание |
|---|---|
| `VPS_HOST` | IP-адрес VPS |
| `VPS_USER` | SSH-пользователь (root) |
| `VPS_SSH_KEY` | Приватный SSH-ключ |
| `VPS_PORT` | SSH-порт (22) |

### 6.4. Ручной деплой

Если GitHub Actions недоступен:
```bash
ssh root@<VPS_IP>
cd /opt/salescopilot
git pull origin main
chmod +x deploy.sh
./deploy.sh
```

---

## 7. Production: конфигурация на VPS

### 7.1. Структура на сервере

```text
/opt/salescopilot/
  backend/
    .env              # Production API-ключи (PORT=8211, DASHBOARD_URL=http://enotai.ru:3211)
    venv/             # Python virtualenv
  dashboard/
    dist/             # Собранный фронтенд (npm run build)
    dist/version.json # Генерируется deploy.sh
  deploy.sh           # Скрипт деплоя
```

### 7.2. Systemd

```text
/etc/systemd/system/salescopilot-backend.service
```

Основные параметры:
- `WorkingDirectory=/opt/salescopilot/backend`
- `ExecStart=...uvicorn main:app --host 0.0.0.0 --port 8211`
- `EnvironmentFile=/opt/salescopilot/backend/.env`

Команды:
```bash
systemctl status salescopilot-backend
systemctl restart salescopilot-backend
journalctl -u salescopilot-backend -f   # логи
```

### 7.3. Nginx

Nginx слушает порт **3211** и отдаёт:
- Статику дашборда из `/opt/salescopilot/dashboard/dist/`
- Проксирует `/api/` и `/ws/` на бэкенд (`127.0.0.1:8211`)

### 7.4. Production `.env` (backend)

Ключевые отличия от dev:
```bash
PORT=8211
DEBUG=false
DASHBOARD_URL=http://enotai.ru:3211   # Для CORS!
ASTERISK_HOST=127.0.0.1               # Asterisk на том же сервере
ASTERISK_AMI_PASSWORD=<secret>
```

> **ВАЖНО:** `DASHBOARD_URL` должен совпадать с URL, через который пользователи открывают дашборд. Иначе CORS заблокирует запросы.

---

## 8. Что дальше

Аудиопоток из Asterisk передаётся через AudioSocket -> STT -> транскрипт -> дашборд.

Осталось:
1. Подключить SIP-транк (Mango Office) к Asterisk
2. Добавить AMI Originate для автоматического запуска AudioSocket при BridgeEnter
3. Реализовать подсказки ИИ на основе транскрипта + классификаторов SpeechKit

---

## 9. Выученные уроки (Lessons Learned)

Практические уроки, извлечённые при разработке и деплое. Помогут избежать повторных ошибок.

### 9.1. Deploy: всегда проверяй, что ВСЕ файлы существуют

**Проблема:** GitHub Actions ссылался на `/opt/salescopilot/deploy.sh`, но файл не был создан -- ни в репозитории, ни на сервере. Результат: `exit code 127` ("command not found").

**Урок:** Перед первым деплоем проверь: все ли скрипты, конфиги, директории (`venv/`, `node_modules/`) реально существуют на сервере. CI/CD не создаст их сам.

### 9.2. Типы возврата: `bool` != `dict`

**Проблема:** Эндпоинт `/api/check-keys` делал `**stt_status`, но `stt.check_connection()` возвращал `bool`, а не `dict`. Результат: 500 Internal Server Error.

**Урок:** Всегда проверяй тип возвращаемого значения при использовании spread-оператора (`**`). Если методы одинаково называются (`check_connection`), это не значит, что они возвращают одинаковый тип.

### 9.3. .env.example должен быть полным

**Проблема:** `config.py` поддерживал `ASTERISK_AMI_PASSWORD`, `AUDIOSOCKET_PORT`, но `.env.example` их не содержал. Новый разработчик не узнает об этих переменных.

**Урок:** При добавлении нового поля в `Settings` (Pydantic) -- сразу добавляй его в `.env.example` с описанием.

### 9.4. CORS: production URL должен быть в allowed_origins

**Проблема:** `allowed_origins` содержал только `localhost:5173`. На продакшене запросы с `http://enotai.ru:3211` блокировались CORS.

**Урок:** Переменная `DASHBOARD_URL` должна быть обязательно задана в production `.env`. Проверяй CORS при первом деплое через DevTools -> Network -> заголовок `Access-Control-Allow-Origin`.

### 9.5. Документация устаревает при рефакторинге

**Проблема:** После рефакторинга в FSD-структуру (`src/app/App.tsx`, `src/shared/`, `src/pages/`) документация ссылалась на старые пути (`src/App.tsx`, `src/hooks/`, `src/types.ts`).

**Урок:** При рефакторинге структуры -- сразу обновлять `system_guide.md`, `agents.md` и README. Иначе документация вводит в заблуждение.

### 9.6. Verify-шаг не должен падать на второстепенных проверках

**Проблема:** Шаг verify в GitHub Actions проверял `cat version.json`, но файл мог не существовать на первом деплое.

**Урок:** Критические проверки (сервис работает, health check отвечает) -- с `|| exit 1`. Информационные проверки (версия, метрики) -- с `|| echo "not found"` (не ломать деплой).
