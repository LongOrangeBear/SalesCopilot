# AI-Копилот Продажник -- Технический справочник (для разработчиков)

Этот файл содержит техническую детализацию, ссылки на документацию и заметки по MCP SDK. Не для презентации -- для разработки.

---

## Документация Bitrix24 (проверенные ссылки)

### REST API Телефонии

| Документ | Ссылка |
|---|---|
| Обзор телефонии REST API | [apidocs.bitrix24.ru/.../telephony](https://apidocs.bitrix24.ru/api-reference/telephony/index.html) |
| PAGE_BACKGROUND_WORKER (сценарий встройки WebRTC) | [apidocs.bitrix24.ru/.../page-background-worker](https://apidocs.bitrix24.ru/api-reference/widgets/ui-interaction/page-background-worker/index.html) |
| WebRTC-интеграция (виджет телефонии) | [apidocs.bitrix24.ru/.../webrtc](https://apidocs.bitrix24.ru/api-reference/widgets/telephony/webrtc.html) |
| telephony.externalCall.register | [apidocs.bitrix24.ru/.../telephony-external-call-register](https://apidocs.bitrix24.ru/api-reference/telephony/telephony-external-call-register.html) |
| telephony.externalCall.finish | [apidocs.bitrix24.ru/.../telephony-external-call-finish](https://apidocs.bitrix24.ru/api-reference/telephony/telephony-external-call-finish.html) |
| telephony.externalCall.attachRecord | [apidocs.bitrix24.ru/.../telephony-external-call-attach-record](https://apidocs.bitrix24.ru/api-reference/telephony/telephony-external-call-attach-record.html) |
| События карточки звонка (BackgroundCallCard) | [apidocs.bitrix24.ru/.../events](https://apidocs.bitrix24.ru/api-reference/widgets/ui-interaction/page-background-worker/events/index.html) |
| Bitrix24 MCP SDK (для разработчиков) | [apidocs.bitrix24.ru/sdk/mcp](https://apidocs.bitrix24.ru/sdk/mcp.html) |

### CoPilot / AI в Bitrix24

| Документ | Ссылка |
|---|---|
| BitrixGPT в CRM: транскрибация и анализ звонков | [helpdesk.bitrix24.ru/open/18799442](https://helpdesk.bitrix24.ru/open/18799442/) |
| BitrixGPT: транскрибация и заполнение полей CRM | [helpdesk.bitrix24.ru/open/27105168](https://helpdesk.bitrix24.ru/open/27105168/) |
| Скрипты продаж и речевая аналитика с ИИ | [helpdesk.bitrix24.ru/open/23240682](https://helpdesk.bitrix24.ru/open/23240682/) |
| BitrixGPT: речевая аналитика для видеозвонков | [helpdesk.bitrix24.ru/open/23529044](https://helpdesk.bitrix24.ru/open/23529044/) |
| MCP в Bitrix24 (для разработчиков) | [helpdesk.bitrix24.ru/open/27050746](https://helpdesk.bitrix24.ru/open/27050746/) |
| MCP Hub: подключение внешних сервисов | [helpdesk.bitrix24.ru/open/26999176](https://helpdesk.bitrix24.ru/open/26999176/) |

---

## Bitrix24 MCP SDK -- ускорение разработки

Bitrix24 выпустил [MCP-сервер](https://apidocs.bitrix24.ru/sdk/mcp.html) -- инструмент, который даёт AI-ассистентам в среде разработки (Cursor, VS Code Copilot, Claude Desktop, Gemini, Antigravity) прямой доступ к **актуальной документации** REST API Bitrix24.

**Подключение:** `https://mcp-dev.bitrix24.tech/mcp`

**Что это нам даёт:**
- При написании CRM-адаптера (создание лидов, задач, сделок, работа с таймлайном) -- AI-ассистент генерирует **корректный** код с правильными методами и параметрами Bitrix24
- Не нужно постоянно сверяться с документацией вручную

**Чего MCP НЕ делает:**
- Не помогает с потоковым аудио -- это задача Asterisk / WebRTC
- Не выполняет запросы к API (он только предоставляет документацию, а не данные)
- Это инструмент для **разработчика**, а не для конечного пользователя

**Итого:** MCP ускоряет написание CRM-интеграции (задачи, лиды, сделки, таймлайн, телефония), но задачу перехвата звука решает Asterisk (Путь 1) или WebRTC (Путь 2).

---

## Путь 2: WebRTC внутри Bitrix24 -- техническая детализация

### Как это работает технически

1. Наше приложение регистрируется в Bitrix24 через `placement.bind` с типом `PAGE_BACKGROUND_WORKER`
2. На каждой странице Битрикса загружается наш невидимый iframe
3. При звонке мы вызываем `telephony.externalcall.register` -- Bitrix24 показывает карточку звонка
4. Наш WebRTC-клиент получает `MediaStream` через стандартное WebRTC API
5. Через `AudioContext` + `ScriptProcessorNode` мы перехватываем сырые PCM-данные
6. Отправляем по WebSocket на наш бэкенд
7. Дальше всё то же: Yandex SpeechKit -> LLM -> подсказки -> виджет
8. При завершении -- `telephony.externalcall.finish`

### Этапы реализации Пути 2

**Этап 2.1 -- Приложение в Bitrix24**
Регистрируем приложение, настраиваем `PAGE_BACKGROUND_WORKER`, проверяем, что наш скрипт загружается на каждой странице портала.

> Контрольная точка: при открытии любой страницы Bitrix24 в консоли браузера видно, что наш background-скрипт запущен.

**Этап 2.2 -- WebRTC-клиент + перехват аудио**
Пишем минимальный WebRTC-клиент. При входящем звонке вызываем `telephony.externalcall.register`, перехватываем `MediaStream`, стримим PCM на бэкенд.

> Контрольная точка: при звонке в Bitrix24 -- аудиочанки приходят на наш бэкенд. В логах видно сырые данные.

**Этап 2.3 -- Полный пайплайн**
Подключаем STT, интенты, подсказки, виджет -- всё то же, что и в Пути 1.

> Контрольная точка: менеджер звонит из Bitrix24, видит подсказки в виджете прямо внутри CRM.

---

## После MVP -- следующие шаги

То, что сознательно не входит в MVP, но запланировано на следующие итерации:

**Метрики и аналитика:**
- Среднее время от реплики клиента до подсказки
- Конверсия сделок до и после внедрения системы
- Количество звонков, где клиент "ушёл" (отказ / нет продолжения)
- Количество подсказок на звонок, латентность, длительность звонка
- Были ли нажаты кнопки действий (отправить КП, создать сделку и т.д.)
- Простой дашборд для визуализации

**Качество подсказок:**
- Подавление подсказок, когда менеджер уже говорит (проверяем по его аудиопотоку: тишина = можно показать, говорит = подавить)
- Уровни уверенности: показывать только подсказки с confidence выше порога -- лучше мало, но точных

**Безопасность и масштабирование:**
- Rate limiting LLM-запросов (защита от зацикливания и перерасхода бюджета)
- Аудит-лог: кто подключался, когда, к каким звонкам
- Шифрование SIP-трафика (SRTP/TLS)

**Детальная документация по ревью архитектуры** -- в файле `architecture_review.md`.
