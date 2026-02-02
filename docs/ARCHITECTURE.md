# Архитектура приложения Teacher App

## Общая схема

```
+------------------------------------------------------------------+
|                      TELEGRAM ECOSYSTEM                           |
+------------------------------------------------------------------+
|                                                                   |
|   +-------------------+              +-------------------+        |
|   |   Telegram Mini   |              |   Telegram Bot    |        |
|   |   App (WebApp)    |<------------>|    (aiogram 3)    |        |
|   |                   |              |                   |        |
|   | - React 18 + TS   |              | - /start, /help   |        |
|   | - Vite bundler    |              | - /teachers       |        |
|   | - React Router    |              | - /deadlines      |        |
|   | - Calendar UI     |              | - /upload         |        |
|   | - TG WebApp SDK   |              | - FSM states      |        |
|   +--------+----------+              +--------+----------+        |
|            |                                  |                   |
|            +---------------+------------------+                   |
|                            |                                      |
+----------------------------|--------------------------------------+
                             | HTTP REST API
                             v
+------------------------------------------------------------------+
|                      FASTAPI BACKEND                              |
+------------------------------------------------------------------+
|                                                                   |
|   +----------------------------------------------------------+   |
|   |                      main.py (Lifespan)                   |   |
|   |  - CORS middleware                                        |   |
|   |  - DB initialization                                      |   |
|   |  - APScheduler start                                      |   |
|   |  - Bot polling                                            |   |
|   +----------------------------------------------------------+   |
|                            |                                      |
|        +-------------------+-------------------+                   |
|        |                   |                   |                   |
|        v                   v                   v                   |
|   +---------+        +-----------+       +-----------+            |
|   | Routes  |        | Services  |       | Bot Module|            |
|   +---------+        +-----------+       +-----------+            |
|   |         |        |           |       |           |            |
|   | /api/   |        | GPTService|       | handlers/ |            |
|   | teachers|        | (OpenAI)  |       | states/   |            |
|   | subjects|        |           |       | callbacks |            |
|   | deadlines        | Reminder  |       |           |            |
|   | schedule |        | Service   |       |           |            |
|   | materials|        |           |       |           |            |
|   | notes   |        |           |       |           |            |
|   | settings|        |           |       |           |            |
|   | semester|        |           |       |           |            |
|   +---------+        +-----------+       +-----------+            |
|        |                   |                   |                   |
|        +-------------------+-------------------+                   |
|                            |                                      |
|   +----------------------------------------------------------+   |
|   |              SQLAlchemy 2 (Async ORM)                     |   |
|   +----------------------------------------------------------+   |
|   |                                                           |   |
|   |  +-------+  +--------+  +----------+  +----------+       |   |
|   |  | User  |  |Subject |  | Teacher  |  | Deadline |       |   |
|   |  +-------+  +--------+  +----------+  +----------+       |   |
|   |       |          |            |             |             |   |
|   |       +----------+------------+-------------+             |   |
|   |                  |                                        |   |
|   |  +---------------+---------------+---------------+        |   |
|   |  |               |               |               |        |   |
|   |  v               v               v               v        |   |
|   | +------+  +----------+  +---------+  +----------+        |   |
|   | | Note |  | Material |  | Schedule|  | Reminder |        |   |
|   | +------+  +----------+  +---------+  +----------+        |   |
|   |                                                           |   |
|   +----------------------------------------------------------+   |
|                                                                   |
|   +----------------------------------------------------------+   |
|   |           APScheduler (Background Tasks)                  |   |
|   |  - Every 5 min: check_and_send_reminders()               |   |
|   |  - Query pending reminders                                |   |
|   |  - Send via Telegram Bot API                             |   |
|   +----------------------------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+----------------+   +----------------+   +----------------+
|   PostgreSQL   |   |  OpenAI API    |   |  Telegram API  |
|   Database     |   |  (GPT-4o-mini) |   |                |
+----------------+   +----------------+   +----------------+
| - Users        |   | - parse_note   |   | - send_message |
| - Subjects     |   | - generate_hint|   | - callbacks    |
| - Teachers     |   | - summarize    |   | - file upload  |
| - Deadlines    |   | - parse_data   |   | - WebApp SDK   |
| - Materials    |   +----------------+   +----------------+
| - Schedules    |
| - Notes        |
| - Reminders    |
| - Settings     |
+----------------+
```

## Схема моделей данных

```
+------------------+       +------------------+       +------------------+
|      USER        |       |     SUBJECT      |       |     TEACHER      |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| telegram_id (UK) |<--+   | user_id (FK)     |------>| user_id (FK)     |
| username         |   |   | name             |       | name             |
| first_name       |   |   | description      |       | temperament      |
| created_at       |   |   | ai_summary       |       | preferences      |
+------------------+   |   | created_at       |       | notes            |
         |             |   +------------------+       | contact_info     |
         |             |            |                 | created_at       |
         |             |            |                 +------------------+
         |             |            |                          |
         v             |            v                          v
+------------------+   |   +------------------+       +------------------+
| REMINDER_SETTINGS|   |   | SUBJECT_TEACHER  |       |                  |
+------------------+   |   +------------------+       |   (Many-to-Many  |
| id (PK)          |   |   | id (PK)          |<------+    via S_T)      |
| user_id (FK, UK) |---+   | subject_id (FK)  |       |                  |
| hours_before []  |       | teacher_id (FK)  |       +------------------+
| is_enabled       |       | role             |
+------------------+       +------------------+
                                   |
         +-------------------------+
         |
         v
+------------------+       +------------------+       +------------------+
|    DEADLINE      |       |    MATERIAL      |       |    SCHEDULE      |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| subject_id (FK)  |       | subject_id (FK)  |       | user_id (FK)     |
| title            |       | material_type    |       | subject_id (FK)  |
| work_type        |       | title            |       | day_of_week      |
| description      |       | description      |       | start_time       |
| ai_hint          |       | content_text     |       | end_time         |
| deadline_date    |       | ai_summary       |       | lesson_type      |
| is_completed     |       | scheduled_date   |       | pair_number      |
| created_at       |       | order_index      |       | is_recurring     |
+------------------+       | created_at       |       | specific_date    |
         |                 +------------------+       | created_at       |
         |                                           +------------------+
         v
+------------------+       +------------------+
|    REMINDER      |       |      NOTE        |
+------------------+       +------------------+
| id (PK)          |       | id (PK)          |
| deadline_id (FK) |       | user_id (FK)     |
| hours_before     |       | subject_id (FK)  |
| send_at          |       | teacher_id (FK)  |
| is_sent          |       | note_type        |
| message          |       | raw_text         |
| created_at       |       | parsed_data      |
+------------------+       | is_processed     |
                           | created_at       |
                           +------------------+
```

## Потоки данных

### 1. Создание заметки через бот

```
+--------+    Сообщение     +--------+    parse_note()    +--------+
|  User  | ---------------> |  Bot   | -----------------> | GPT-4  |
+--------+                  +--------+                    +--------+
                                |                              |
                                |    {teacher, deadline,       |
                                |     note_type, enhanced}     |
                                | <----------------------------+
                                |
                                v
                    +------------------------+
                    |   Создание в БД:       |
                    |   - Note               |
                    |   - Subject (если нет) |
                    |   - Teacher (если нет) |
                    |   - SubjectTeacher     |
                    |   - Deadline           |
                    |   - Reminders          |
                    +------------------------+
                                |
                                v
                    +------------------------+
                    |  Подтверждение в TG    |
                    +------------------------+
```

### 2. Напоминание о дедлайне

```
+-------------+     Every 5 min      +------------------+
| APScheduler | -------------------> | check_reminders  |
+-------------+                      +------------------+
                                              |
                                              v
                                     +------------------+
                                     | get_pending()    |
                                     | is_sent = False  |
                                     | send_at <= now   |
                                     +------------------+
                                              |
                                              v
                                     +------------------+
                                     | For each:        |
                                     |  - Generate msg  |
                                     |  - Send to TG    |
                                     |  - Mark as sent  |
                                     +------------------+
                                              |
                                              v
                                     +------------------+
                                     |  User receives   |
                                     |  notification    |
                                     +------------------+
```

### 3. Загрузка расписания Frontend

```
+----------+    mount()     +-----------+    GET /api/schedule    +---------+
|  React   | -------------> | useEffect | ----------------------> | FastAPI |
| Calendar |                +-----------+                         +---------+
+----------+                                                           |
     ^                                                                 |
     |                                                                 v
     |                                                      +------------------+
     |                                                      | Query DB:        |
     |                                                      | - Validate user  |
     |                                                      | - SELECT schedule|
     |                                                      | - JOIN subject   |
     |                                                      +------------------+
     |                                                                 |
     |    [ScheduleResponse]                                          |
     +----------------------------------------------------------------+
```

## API Endpoints

| Группа | Метод | Endpoint | Описание |
|--------|-------|----------|----------|
| **Teachers** | GET | `/api/teachers` | Получить всех преподавателей |
| | GET | `/api/teachers/{id}` | Получить преподавателя |
| | POST | `/api/teachers` | Создать преподавателя |
| | PUT | `/api/teachers/{id}` | Обновить преподавателя |
| | DELETE | `/api/teachers/{id}` | Удалить преподавателя |
| **Subjects** | GET | `/api/subjects` | Получить все предметы |
| | GET | `/api/subjects/{id}` | Получить предмет |
| | POST | `/api/subjects` | Создать предмет |
| | DELETE | `/api/subjects/{id}` | Удалить предмет |
| | POST | `/api/subjects/{id}/link-teacher` | Привязать преподавателя |
| | DELETE | `/api/subjects/{id}/unlink-teacher/{tid}` | Отвязать преподавателя |
| | POST | `/api/subjects/{id}/summary` | AI выжимка |
| **Deadlines** | GET | `/api/deadlines` | Получить дедлайны |
| | POST | `/api/deadlines` | Создать дедлайн |
| | PUT | `/api/deadlines/{id}` | Обновить дедлайн |
| | DELETE | `/api/deadlines/{id}` | Удалить дедлайн |
| **Schedule** | GET | `/api/schedule` | Получить расписание |
| | POST | `/api/schedule` | Создать занятие |
| | DELETE | `/api/schedule/{id}` | Удалить занятие |
| **Materials** | GET | `/api/materials` | Получить материалы |
| | POST | `/api/materials` | Создать материал |
| | DELETE | `/api/materials/{id}` | Удалить материал |
| **Notes** | GET | `/api/notes` | Получить заметки |
| **Semester** | POST | `/api/semester/upload-text` | Загрузить текст |
| | POST | `/api/semester/upload-file` | Загрузить файл |
| | POST | `/api/semester/upload-json` | Загрузить JSON |
| **Settings** | GET | `/api/settings/reminders` | Настройки напоминаний |
| | PUT | `/api/settings/reminders` | Обновить настройки |

## Технологический стек

```
+------------------------------------------------------------------+
|                          FRONTEND                                 |
+------------------------------------------------------------------+
| React 18         | UI библиотека                                 |
| TypeScript       | Типизация                                     |
| Vite             | Сборщик                                       |
| React Router     | Маршрутизация                                 |
| Axios            | HTTP клиент                                   |
| date-fns         | Работа с датами                               |
| @twa-dev/sdk     | Telegram WebApp SDK                           |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                          BACKEND                                  |
+------------------------------------------------------------------+
| FastAPI          | Web framework                                  |
| SQLAlchemy 2     | Async ORM                                     |
| aiogram 3        | Telegram Bot framework                        |
| APScheduler      | Background tasks                              |
| OpenAI           | GPT-4o-mini интеграция                        |
| pytz             | Часовые пояса (Europe/Moscow)                 |
| asyncpg          | PostgreSQL async driver                       |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                          DATABASE                                 |
+------------------------------------------------------------------+
| PostgreSQL 15    | Основная БД                                   |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                          DEPLOYMENT                               |
+------------------------------------------------------------------+
| Docker           | Контейнеризация                               |
| Docker Compose   | Оркестрация                                   |
+------------------------------------------------------------------+
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Инициализация, создание пользователя |
| `/help` | Справка по командам |
| `/teachers` | Список всех преподавателей |
| `/deadlines` | Список активных дедлайнов |
| `/summary` | Выбрать предмет для AI-выжимки |
| `/upload` | Загрузить данные семестра |
| `/settings` | Настроить напоминания |
| `/cancel` | Отменить текущую операцию |

## Frontend маршруты

| Путь | Компонент | Описание |
|------|-----------|----------|
| `/` | CalendarPage | Главная - календарь с расписанием и дедлайнами |
| `/subjects` | SubjectsPage | Список предметов |
| `/subjects/:id` | SubjectDetailPage | Детали предмета |
| `/teachers` | TeachersPage | Список преподавателей |
| `/teachers/:id` | TeacherDetailPage | Детали преподавателя |
| `/settings` | SettingsPage | Настройки приложения |

## Настройки по умолчанию

- **Напоминания:** 72ч, 24ч, 12ч до дедлайна
- **Часовой пояс:** Europe/Moscow (UTC+3)
- **Роли преподавателей:** lecturer, practitioner
- **Типы материалов:** lecture, practice, lab, test, exam, other
- **Типы заметок:** note, preference, tip, material
