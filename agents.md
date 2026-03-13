# SalesCopilot -- правила для работы через AI

Этот файл содержит обязательные правила для всех AI-ассистентов, работающих с кодовой базой SalesCopilot.

## Общие правила

1. **Кириллица** -- все комментарии, UI-текст, логи и документация на русском языке (кириллица). Транслитерация запрещена.
2. **Credentials** -- при добавлении/изменении любых доступов (API-ключи, пароли, хосты) обновлять `credentials.md` в корне проекта.
3. **Без эмоджи** -- не использовать 4-байтные UTF-8 символы (эмоджи, иконки) в коде и документации. Использовать `[v]`, `[x]`, `[!]` или ASCII-символы.
4. **Без browser-проверок** -- не открывать браузер для визуальной проверки, пока пользователь явно не попросит. Проверять только через build-команды (`npm run build`, `python3 -c "from app import create_app"`).

## Архитектурные правила

### Перед началом работы
1. Прочитать `agents.md` в соответствующей директории (backend/, dashboard/) для понимания архитектурных ограничений.
2. Следовать существующим паттернам и структуре проекта.

### Backend (Python / FastAPI)
- Структура описана в `backend/agents.md`
- Основной принцип: модульная архитектура с разделением на слои (routes, services, models, core)

### Frontend (React / TypeScript / Tailwind)
- Структура описана в `dashboard/agents.md`
- Основной принцип: Feature Sliced Design (FSD) со строгим соблюдением слоёв

### Asterisk (PJSIP)

Конфиги: `/etc/asterisk/` на VPS `5.45.112.38`. Workflow: `/asterisk`.

**Критические правила:**

1. **Имя endpoint = SIP username.** PJSIP идентифицирует endpoint по полю `From` в SIP-запросе. Если софтфон отправляет `From: sip:manager@...`, endpoint в `pjsip.conf` должен называться `[manager]`, а не `[100]`. Несовпадение = 401 Unauthorized.
2. **Dialplan привязан к endpoint-именам.** При переименовании endpoint'ов обязательно обновить `extensions.conf` -- `Dial(PJSIP/<endpoint_name>)`.
3. **Бэкап перед редактированием.** Всегда `cp *.conf *.conf.bak` перед изменениями.
4. **Reload вместо restart.** Использовать `asterisk -rx 'core reload'` -- не рвёт активные звонки. Полный `systemctl restart asterisk` только если менялись транспорты.
5. **После изменений -- обязательная проверка:**
   - `pjsip show endpoints` -- статус "Not in use" = зарегистрирован, "Unavailable" = не подключен
   - `pjsip show auths` -- проверка аутентификации
   - `dialplan show internal` -- проверка маршрутизации

**Выученные уроки:**

- [2026-03-13] PJSIP endpoint identifier (`res_pjsip_endpoint_identifier_user`) сопоставляет username из заголовка `From` SIP-запроса с именем секции endpoint в `pjsip.conf`. Если софтфон шлёт `From: sip:client@server`, а endpoint назван `[200]` -- Asterisk не найдёт endpoint и вернёт 401. Решение: именовать секции endpoint по SIP-логину (`[manager]`, `[client]`), а не по номеру расширения.
- [2026-03-13] warnings "Dropping N bytes packet -- PJSIP syntax error" от UDP-пакетов -- это STUN/keep-alive от Zoiper, безобидный шум, игнорировать.
- [2026-03-13] Лог-файл Asterisk: `/var/log/asterisk/messages.log` (не `messages`, не `full`). Для отладки SIP: `asterisk -rx 'pjsip set logger on'`.

## Чеклист перед коммитом

- [ ] Код компилируется без ошибок (backend: `python3 -c "from app import create_app"`, frontend: `npm run build`)
- [ ] Нет транслитерации в коде
- [ ] `credentials.md` обновлён (если менялись доступы)
- [ ] Изменения соответствуют архитектуре (проверить agents.md)
