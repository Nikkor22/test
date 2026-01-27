from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pytz

from app.models import Deadline, Reminder, ReminderSettings, User, Subject, Teacher
from app.services.gpt_service import GPTService

MOSCOW_TZ = pytz.timezone('Europe/Moscow')


class ReminderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.gpt = GPTService()

    async def create_reminders_for_deadline(self, deadline: Deadline, user_id: int) -> list[Reminder]:
        """Создает напоминания для дедлайна на основе настроек пользователя."""
        settings_result = await self.session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user_id)
        )
        settings = settings_result.scalar_one_or_none()

        hours_before_list = settings.hours_before if settings else [72, 24, 12]

        reminders = []
        for hours in hours_before_list:
            send_at = deadline.deadline_date - timedelta(hours=hours)

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

        # Get teachers for this subject
        teachers_result = await self.session.execute(
            select(Teacher).where(Teacher.subject_id == subject.id)
        )
        teachers = teachers_result.scalars().all()

        deadline_info = {
            "subject": subject.name if subject else "Неизвестно",
            "title": deadline.title,
            "work_type": deadline.work_type,
            "deadline_date": deadline.deadline_date.strftime("%d.%m.%Y %H:%M"),
            "description": deadline.description or "",
            "gpt_description": deadline.gpt_description or ""
        }

        teacher_info = None
        if teachers:
            t = teachers[0]
            teacher_info = {
                "name": t.name,
                "role": t.role,
                "temperament": t.temperament,
                "preferences": t.preferences,
                "peculiarities": t.peculiarities,
                "notes": t.notes
            }

        hours_left = reminder.hours_before
        if hours_left >= 24:
            time_left = f"{hours_left // 24} дн."
        else:
            time_left = f"{hours_left} ч."

        # Use smart advert for reminders
        message = await self.gpt.generate_smart_advert(deadline_info, teacher_info)
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
