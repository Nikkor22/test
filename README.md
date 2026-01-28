# Student Planner - Telegram Bot + Mini App

Персональное приложение для студента с Telegram ботом и Mini App для планирования учёбы.

## Возможности

### Основные функции
- **Календарь** - главная страница с недельным видом, расписанием и дедлайнами
- **Предметы** - список предметов с привязкой преподавателей (лектор/практикант)
- **Преподаватели** - профили с характером, предпочтениями и контактами
- **AI-функции** - автоматический парсинг заметок, генерация подсказок и выжимок

### AI возможности (GPT-4o-mini)
- Парсинг свободного текста в структурированные данные
- Генерация AI-подсказок для дедлайнов
- AI-выжимка по предмету для подготовки к экзамену
- Bulk-парсинг данных семестра (расписание, материалы)

### Telegram Bot
- Свободный ввод заметок о преподавателях и дедлайнах
- Загрузка данных семестра (текст, JSON, PDF)
- `/summary` - AI-сводка по предмету
- `/upload` - загрузка файлов семестра
- Напоминания о дедлайнах

### Mini App (4 вкладки)
- **Календарь** - недельный вид, расписание дня, дедлайны с AI-подсказками
- **Предметы** - детальные страницы с заметками по типам
- **Преподаватели** - профили с переходом к предметам
- **Настройки** - напоминания и загрузка семестра

## Технологии

### Backend
- Python 3.11
- FastAPI + aiogram 3
- SQLAlchemy 2 (async) + PostgreSQL
- OpenAI GPT-4o-mini
- PyMuPDF (PDF парсинг)
- APScheduler

### Frontend
- React 18 + TypeScript
- React Router
- Vite
- Telegram WebApp SDK
- date-fns

## Быстрый старт

### 1. Настройка переменных окружения

```bash
cp backend/.env.example backend/.env
```

Заполните `backend/.env`:
```env
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
WEBAPP_URL=https://your-domain.com
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/teacher_app
```

### 2. Запуск через Docker (рекомендуется)

```bash
# Скопировать .env файл
cp backend/.env.example backend/.env
# Отредактировать backend/.env и добавить BOT_TOKEN и OPENAI_API_KEY

# Запустить все сервисы
docker-compose up -d
```

Сервисы:
- PostgreSQL: `localhost:5432`
- Backend API: `localhost:8000`
- Frontend: `localhost:5173`

### 3. Локальный запуск (без Docker)

#### База данных:
```bash
# Установите PostgreSQL и создайте базу
createdb teacher_app
```

#### Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы, открытие Mini App |
| `/teachers` | Список преподавателей |
| `/deadlines` | Список дедлайнов |
| `/summary` | AI-сводка по предмету |
| `/upload` | Загрузка данных семестра |
| `/settings` | Настройки напоминаний |
| `/help` | Справка |

## Примеры использования

### Заметки боту (свободный текст)

**О преподавателе:**
```
Петров по матану строгий, любит спрашивать теорию. Можно писать на petrov@mail.ru
```

**Дедлайн:**
```
Контрольная по физике 15 февраля в 10:00
Лабораторная №3 по программированию сдать до 20.02
```

### Загрузка семестра

Можно отправить боту файл (PDF/JSON/TXT) или текст с расписанием:
```
Понедельник:
09:00-10:30 Математика (лекция) - Иванов
10:45-12:15 Физика (практика) - Петрова

Среда:
09:00-10:30 Программирование (лаб) - Сидоров
```

### JSON формат семестра

```json
{
  "subjects": [
    {
      "name": "Математика",
      "teachers": [
        {"name": "Иванов И.И.", "role": "lecturer"},
        {"name": "Петрова А.С.", "role": "practitioner"}
      ],
      "schedule": [
        {"day_of_week": 0, "start_time": "09:00", "end_time": "10:30", "lesson_type": "lecture"}
      ],
      "materials": [
        {"type": "lecture", "title": "Введение в анализ", "date": "2024-02-01"}
      ]
    }
  ]
}
```

## API Endpoints

### Subjects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/subjects` | Список предметов |
| GET | `/api/subjects/{id}` | Детали предмета |
| POST | `/api/subjects` | Создать предмет |
| DELETE | `/api/subjects/{id}` | Удалить предмет |
| POST | `/api/subjects/{id}/summary` | Сгенерировать AI-выжимку |

### Teachers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/teachers` | Список преподавателей |
| GET | `/api/teachers/{id}` | Детали преподавателя |
| POST | `/api/teachers` | Создать преподавателя |
| PUT | `/api/teachers/{id}` | Обновить преподавателя |
| DELETE | `/api/teachers/{id}` | Удалить преподавателя |

### Deadlines
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/deadlines` | Список дедлайнов |
| POST | `/api/deadlines` | Создать дедлайн |
| PUT | `/api/deadlines/{id}` | Обновить дедлайн |
| DELETE | `/api/deadlines/{id}` | Удалить дедлайн |

### Schedule & Materials
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schedule` | Расписание |
| POST | `/api/schedule` | Добавить занятие |
| GET | `/api/materials` | Материалы семестра |
| POST | `/api/materials` | Добавить материал |

### Semester Upload
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/semester/upload-text` | Загрузить текст |
| POST | `/api/semester/upload-file` | Загрузить файл (PDF/JSON/TXT) |

### Notes & Settings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notes` | Заметки (фильтр по типу) |
| GET | `/api/settings/reminders` | Настройки напоминаний |
| PUT | `/api/settings/reminders` | Обновить настройки |

## Структура проекта

```
.
├── backend/
│   ├── app/
│   │   ├── bot/           # Telegram bot (aiogram 3)
│   │   ├── models/        # SQLAlchemy models
│   │   ├── routers/       # FastAPI routes
│   │   ├── services/      # GPT, reminders
│   │   └── config.py
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── pages/
│   │   │   ├── CalendarPage.tsx
│   │   │   ├── SubjectsPage.tsx
│   │   │   ├── SubjectDetailPage.tsx
│   │   │   ├── TeachersPage.tsx
│   │   │   ├── TeacherDetailPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── styles/
│   │   └── App.tsx
│   └── package.json
└── docker-compose.yml
```

## Деплой

### HTTPS для Mini App

Telegram Mini App требует HTTPS:

1. **ngrok** (разработка):
   ```bash
   ngrok http 5173
   ```

2. **Cloudflare Tunnel** (бесплатно)

3. **VPS + Nginx + Let's Encrypt**

### Настройка бота

1. Создайте бота через @BotFather
2. Получите токен
3. Настройте Menu Button: `/setmenubutton` → URL Mini App

## Лицензия

MIT
