import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.base import init_db, async_session
from app.models import User, Reminder, Deadline, Subject, ReminderSettings
from app.routers import router
from app.bot import bot, dp
from app.services.reminder_service import ReminderService

settings = get_settings()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def check_and_send_reminders():
    """Проверяет и отправляет напоминания."""
    print("Checking reminders...")

    async with async_session() as session:
        reminder_service = ReminderService(session)
        pending_reminders = await reminder_service.get_pending_reminders()

        for reminder in pending_reminders:
            try:
                # Получаем пользователя
                deadline = reminder.deadline
                subject = deadline.subject

                result = await session.execute(
                    select(User).where(User.id == subject.user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    continue

                # Проверяем, включены ли напоминания
                result = await session.execute(
                    select(ReminderSettings).where(ReminderSettings.user_id == user.id)
                )
                settings = result.scalar_one_or_none()

                if settings and not settings.is_enabled:
                    continue

                # Генерируем и отправляем сообщение
                message = await reminder_service.generate_reminder_message(reminder)
                await bot.send_message(user.telegram_id, message)

                # Помечаем как отправленное
                await reminder_service.mark_as_sent(reminder, message)

                print(f"Reminder sent to user {user.telegram_id} for deadline {deadline.title}")

            except Exception as e:
                print(f"Error sending reminder: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI."""
    # Startup
    print("Starting up...")

    # Инициализация БД
    await init_db()
    print("Database initialized")

    # Запуск планировщика
    scheduler.add_job(
        check_and_send_reminders,
        trigger=IntervalTrigger(minutes=5),
        id="reminder_checker",
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started")

    # Запуск бота в фоне
    asyncio.create_task(dp.start_polling(bot))
    print("Bot polling started")

    yield

    # Shutdown
    print("Shutting down...")
    scheduler.shutdown()
    await bot.session.close()


app = FastAPI(
    title="Teacher App API",
    description="API для приложения учета преподавателей и дедлайнов",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Teacher App API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
