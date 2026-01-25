# Teacher App - Telegram Bot + Mini App

Приложение для учебы с Telegram ботом и мини-приложением для отслеживания преподавателей и дедлайнов.

## Возможности

- **Заметки через бота**: просто пишите боту информацию о преподавателях и дедлайнах
- **GPT парсинг**: автоматическое извлечение структурированных данных из текста
- **Mini App**: удобный просмотр профилей преподавателей и дедлайнов
- **Напоминания**: настраиваемые уведомления о приближающихся дедлайнах
- **Редактирование**: ручное редактирование всех данных в Mini App

## Технологии

### Backend
- Python 3.11
- FastAPI
- aiogram 3
- SQLAlchemy 2 (async)
- PostgreSQL
- OpenAI GPT-4
- APScheduler

### Frontend
- React 18
- TypeScript
- Vite
- Telegram WebApp SDK

## Запуск

### 1. Настройка переменных окружения

```bash
cp backend/.env.example backend/.env
```

Заполните `.env`:
```
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
WEBAPP_URL=https://your-domain.com  # URL вашего Mini App
```

### 2. Запуск через Docker

```bash
docker-compose up -d
```

Это запустит:
- PostgreSQL на порту 5432
- Backend на порту 8000
- Frontend на порту 5173

### 3. Локальный запуск (без Docker)

#### Backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows
pip install -r requirements.txt
python main.py
```

#### Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Использование

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы |
| `/teachers` | Список преподавателей |
| `/deadlines` | Список дедлайнов |
| `/add_teacher` | Добавить преподавателя |
| `/settings` | Настройки напоминаний |
| `/help` | Справка |

### Примеры заметок

**Информация о преподавателе:**
```
Петров по матану строгий, любит спрашивать теорию
```

**Дедлайн:**
```
Контрольная по физике 15 февраля в 10:00
Лабораторная работа №3 по программированию сдать до 20.02
```

**Комбинированная заметка:**
```
Иванов по истории добрый. Экзамен 25 января, нужно выучить даты
```

## Деплой

### Получение HTTPS для Mini App

Telegram Mini App требует HTTPS. Варианты:

1. **ngrok** (для разработки):
   ```bash
   ngrok http 5173
   ```

2. **Cloudflare Tunnel**

3. **VPS + Nginx + Let's Encrypt**

### Настройка бота в BotFather

1. Создайте бота через @BotFather
2. Получите токен
3. Настройте Menu Button:
   - `/setmenubutton`
   - Выберите бота
   - Отправьте URL вашего Mini App

## Структура проекта

```
.
├── backend/
│   ├── app/
│   │   ├── bot/          # Telegram bot handlers
│   │   ├── models/       # SQLAlchemy models
│   │   ├── routers/      # FastAPI routes
│   │   ├── services/     # Business logic (GPT, reminders)
│   │   └── config.py     # Configuration
│   ├── main.py           # Entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # API client
│   │   ├── pages/        # React pages
│   │   ├── styles/       # CSS
│   │   └── App.tsx
│   └── package.json
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/teachers` | Получить преподавателей |
| PUT | `/api/teachers/{id}` | Обновить преподавателя |
| DELETE | `/api/teachers/{id}` | Удалить преподавателя |
| GET | `/api/deadlines` | Получить дедлайны |
| POST | `/api/deadlines` | Создать дедлайн |
| PUT | `/api/deadlines/{id}` | Обновить дедлайн |
| DELETE | `/api/deadlines/{id}` | Удалить дедлайн |
| GET | `/api/subjects` | Получить предметы |
| POST | `/api/subjects` | Создать предмет |
| GET | `/api/settings/reminders` | Получить настройки |
| PUT | `/api/settings/reminders` | Обновить настройки |

## Лицензия

MIT
