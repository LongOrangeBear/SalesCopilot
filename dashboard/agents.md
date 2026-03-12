# Dashboard -- архитектурные правила (Feature Sliced Design)

## Стек

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 3 + CSS-переменные (дизайн-токены)
- lucide-react (иконки)
- clsx + tailwind-merge (утилита `cn()`)

## Структура проекта (FSD)

```
src/
  app/                     # Верхний слой: провайдеры, глобальные стили
    App.tsx                #   Shell: header + навигация + роутинг по табам
    index.css              #   Глобальные стили, CSS-переменные, анимации
  shared/                  # Общий код без бизнес-логики
    api/                   #   API-клиенты (WS, REST, конфиг URL)
      config.ts            #     WS_URL, API_URL
      ws-client.ts         #     useWebSocket()
      rest-client.ts       #     useApi()
      index.ts
    lib/                   #   Утилиты
      cn.ts                #     cn() -- объединение CSS-классов
      format.ts            #     formatTime(), formatTimestamp()
      index.ts
    types/                 #   Типы данных (зеркало бэкенда)
      index.ts             #     CallSession, WSMessage, HealthResponse, etc.
    ui/                    #   Переиспользуемые UI-компоненты (без бизнес-логики)
      SpeakingIndicator.tsx
      CheckItem.tsx        #     Статус-карточка с иконкой
      index.ts
  entities/                # Бизнес-сущности (тип + минимальный UI)
    call/
      ui/CallListItem.tsx  #   Элемент списка звонков
      index.ts
  widgets/                 # Составные блоки UI (комбинируют entities)
    call-detail/
      ui/CallDetail.tsx    #   Композиция подкомпонентов
      ui/TranscriptPanel.tsx  #   Live-транскрипт
      ui/SessionInfo.tsx      #   CallSession + CRM
      ui/AIRequestsPanel.tsx  #   ИИ запросы и ответы
      ui/PipelineTimingsPanel.tsx  #   Тайминги пайплайна
      index.ts
  features/                # Пользовательские сценарии (фичи)
    system-check/
      ui/ChecklistTab.tsx  #   Чеклист здоровья системы
      index.ts
  pages/                   # Страницы (композиция widgets + features)
    monitor/
      ui/MonitorPage.tsx   #   Список звонков + детали
      index.ts
    checklist/
      ui/ChecklistPage.tsx #   Страница чеклиста
      index.ts
  main.tsx                 # Точка входа React
```

## Правила FSD

### Направление зависимостей
Слои могут импортировать только из слоёв **ниже себя**:

```
pages -> widgets, features, entities, shared
features -> entities, shared
widgets -> entities, shared
entities -> shared
shared -> (ничего из проекта, только внешние пакеты)
```

**Запрещено:**
- `shared/` импортирует из `entities/`
- `entities/` импортирует из `features/` или `widgets/`
- `features/` импортирует из `pages/`

### Правила именования
- Папки слайсов: `kebab-case` (`call-detail`, `system-check`)
- Файлы компонентов: `PascalCase.tsx`
- Файлы утилит/хуков: `camelCase.ts`
- Barrel-экспорт: `index.ts` в каждом слайсе

### Импорты
- Использовать алиас `@/` для абсолютных импортов: `import { cn } from '@/shared/lib'`
- Не использовать `../../../` -- только `@/`

## Правила размещения нового кода

### Новый UI-компонент (кнопка, бейдж, спиннер)
1. Создать файл в `shared/ui/`
2. Экспортировать через `shared/ui/index.ts`

### Новый тип данных
1. Добавить в `shared/types/index.ts`

### Новая бизнес-сущность (transcript, agent, deal)
1. Создать папку `entities/<name>/`
2. Структура: `ui/`, `model/` (опционально), `index.ts`

### Новый виджет (составной блок)
1. Создать папку `widgets/<name>/`
2. Структура: `ui/`, `index.ts`

### Новая фича (пользовательский сценарий)
1. Создать папку `features/<name>/`
2. Структура: `ui/`, `model/` (опционально), `index.ts`

### Новая страница
1. Создать папку `pages/<name>/`
2. Структура: `ui/`, `index.ts`
3. Подключить в `App.tsx`

## Чеклист перед коммитом

- [ ] `npm run build` -- проходит без ошибок
- [ ] `npm run lint` -- без ошибок ESLint
- [ ] Направление зависимостей соблюдено (нет импортов вверх по слоям)
- [ ] Все импорты через `@/` (нет относительных `../../`)
- [ ] Новые компоненты экспортирнованы через barrel `index.ts`
- [ ] Нет inline-компонентов в `App.tsx` (всё разнесено по слоям)
- [ ] Комментарии на русском (кириллица, без транслитерации)
- [ ] `data: any` не используется -- типизировать через discriminated union или generics

## Частые ошибки (из ревью)

### 1. Inline-компоненты внутри фич
Переиспользуемые UI-элементы (статус-карточки, бейджи, индикаторы) не должны определяться внутри компонентов `features/` или `widgets/`. Вынести в `shared/ui/` с barrel-экспортом.

### 2. God-компоненты в виджетах
Если компонент рендерит 3+ визуально независимых блока (транскрипт, CRM, AI, тайминги) -- разбить на отдельные файлы внутри `widgets/<name>/ui/`. Каждый блок = отдельный файл.

### 3. Слой `app/` -- директория
`App.tsx` и `index.css` должны находиться в `src/app/`, а не в `src/`. Это верхний слой FSD, где живут провайдеры и глобальная конфигурация. (Исправлено 2026-03-12)

### 4. Артефакты `create-vite` в коде
После инициализации проекта удалить неиспользуемые файлы из `assets/` (`react.svg`, `vite.svg`, `hero.png`). (Исправлено 2026-03-12)

