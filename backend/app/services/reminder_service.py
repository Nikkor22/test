from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pytz

from app.models import Deadline, Reminder, ReminderSettings, User
from app.services.gpt_service import GPTService

MOSCOW_TZ = pytz.timezone('Europe/Moscow')


class ReminderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.gpt = GPTService()

    async def create_reminders_for_deadline(self, deadline: Deadline, user_id: int) -> list[Reminder]:
        """Создает напоминания для дедлайна на основе настроек пользователя."""
        # Получаем настройки пользователя
        settings_result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        settings = settings_result.scalar_one_or_none()

        # Если настроек нет, используем дефолтные
        hours_before_list = settings.hours_before if settings else [72, 24, 12]

        reminders = []
        for hours in hours_before_list:
            send_at = deadline.deadline_date - timedelta(hours=hours)

            # Не создаем напоминание, если время уже прошло
            now = datetime.now(MOSCOW_TZ).replace(tzinfo=None)
            if send_at <= now:
                continue

            reminder = Reminder(
                deadline_id=deadline.id,
                hours_before=hours,
                send_at=send_at,
                is_sent=False
            )
            self.session.add(reminder)
            reminders.append(reminder)

        await self.session.commit()
        return reminders

    async def get_pending_reminders(self) -> list[Reminder]:
        """Получает все напоминания, которые нужно отправить."""
        now = datetime.now(MOSCOW_TZ).replace(tzinfo=None)

        result = await self.session.execute(
            select(Reminder)
            .options(
                selectinload(Reminder.deadline).selectinload(Deadline.subject)
            )
            .where(Reminder.is_sent == False)
            .where(Reminder.send_at <= now)
        )
        return result.scalars().all()

    async def mark_as_sent(self, reminder: Reminder, message: str):
        """Помечает напоминание как отправленное."""
        reminder.is_sent = True
        reminder.message = message
        await self.session.commit()

    async def generate_reminder_message(self, reminder: Reminder) -> str:
        """Генерирует текст напоминания с помощью GPT."""
        deadline = reminder.deadline
        subject = deadline.subject
        teacher = subject.teacher if subject else None

        deadline_info = {
            "subject": subject.name if subject else "Неизвестно",
            "title": deadline.title,
            "work_type": deadline.work_type,
            "deadline_date": deadline.deadline_date.strftime("%d.%m.%Y %H:%M"),
            "description": deadline.description or ""
        }

        teacher_info = None
        if teacher:
            teacher_info = {
                "name": teacher.name,
                "temperament": teacher.temperament,
                "preferences": teacher.preferences,
                "notes": teacher.notes
            }

        # Определяем сколько времени осталось
        hours_left = reminder.hours_before
        if hours_left >= 24:
            time_left = f"{hours_left // 24} дн."
        else:
            time_left = f"{hours_left} ч."

        message = await self.gpt.generate_reminder(deadline_info, teacher_info)
        return f"⏰ Напоминание (осталось {time_left}):\n\n{message}"

    async def update_user_settings(self, user_id: int, hours_before: list[int]) -> ReminderSettings:
        """Обновляет настройки напоминаний пользователя."""
        result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if settings:
            settings.hours_before = hours_before
        else:
            settings = ReminderSettings(
                user_id=user_id,
                hours_before=hours_before
            )
            self.session.add(settings)

        await self.session.commit()
        return settings
