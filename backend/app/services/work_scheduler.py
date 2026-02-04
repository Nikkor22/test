import os
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pytz

from app.models import (
    User, Subject, Deadline, GeneratedWork,
    UserWorkSettings, TitleTemplate, Material
)
from app.services.gpt_service import GPTService
from app.services.work_generator import WorkGeneratorService

MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Directory for generated files
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)


class WorkSchedulerService:
    def __init__(self, session: AsyncSession, bot=None):
        self.session = session
        self.bot = bot
        self.gpt = GPTService()
        self.generator = WorkGeneratorService(self.gpt)

    async def check_and_generate_works(self):
        """Проверяет дедлайны и автоматически генерирует работы."""
        now = datetime.now(MOSCOW_TZ).replace(tzinfo=None)

        # Get all pending works that need generation
        result = await self.session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject).selectinload(Subject.materials),
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject).selectinload(Subject.user),
                selectinload(GeneratedWork.title_template)
            )
            .where(GeneratedWork.status == "pending")
        )
        pending_works = result.scalars().all()

        for work in pending_works:
            try:
                user = work.deadline.subject.user

                # Get user settings
                settings_result = await self.session.execute(
                    select(UserWorkSettings).where(UserWorkSettings.user_id == user.id)
                )
                settings = settings_result.scalar_one_or_none()

                if not settings or not settings.auto_generate:
                    continue

                # Check if it's time to generate (N days before deadline)
                generate_days_before = settings.generate_days_before if settings else 5
                generate_threshold = work.deadline.deadline_date - timedelta(days=generate_days_before)

                if now < generate_threshold:
                    continue  # Too early to generate

                # Generate the work
                await self._generate_work(work, user)

            except Exception as e:
                print(f"Error generating work {work.id}: {e}")

    async def _generate_work(self, work: GeneratedWork, user: User):
        """Генерирует содержимое работы."""
        work.status = "generating"
        await self.session.commit()

        try:
            # Collect materials
            materials_text = []
            for material in work.deadline.subject.materials:
                if material.parsed_text:
                    materials_text.append(f"=== {material.file_name} ===\n{material.parsed_text}")

            # Generate content
            content = await self.generator.generate_work_content(
                subject_name=work.deadline.subject.name,
                work_type=work.deadline.work_type,
                work_number=work.deadline.work_number,
                title=work.deadline.title,
                description=work.deadline.description,
                materials=materials_text
            )

            # Get template
            template = work.title_template
            if not template:
                template_result = await self.session.execute(
                    select(TitleTemplate).where(
                        TitleTemplate.user_id == user.id,
                        TitleTemplate.is_default == True
                    )
                )
                template = template_result.scalar_one_or_none()

            # Create document
            file_name, file_path = await self.generator.create_document(
                content=content,
                subject_name=work.deadline.subject.name,
                work_type=work.deadline.work_type,
                work_number=work.deadline.work_number,
                student_name=user.first_name or "Студент",
                group_number=user.group_number or "",
                template_path=template.file_path if template else None,
                output_dir=GENERATED_DIR,
                user_id=user.id,
                deadline_id=work.deadline_id
            )

            work.content_text = content
            work.file_name = file_name
            work.file_path = file_path
            work.status = "ready"
            work.generated_at = datetime.utcnow()

            await self.session.commit()

            # Notify user
            if self.bot:
                await self._notify_work_ready(user, work)

        except Exception as e:
            work.status = "pending"  # Reset on error
            await self.session.commit()
            print(f"Work generation failed: {e}")
            raise

    async def _notify_work_ready(self, user: User, work: GeneratedWork):
        """Уведомляет пользователя о готовности работы."""
        if not self.bot:
            return

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        work_type_name = {
            "homework": "Домашняя работа",
            "lab": "Лабораторная работа",
            "practical": "Практическая работа",
            "coursework": "Курсовая работа",
            "report": "Реферат",
        }.get(work.deadline.work_type, work.deadline.work_type)

        work_title = work_type_name
        if work.deadline.work_number:
            work_title += f" №{work.deadline.work_number}"

        message = (
            f"✅ Работа готова!\n\n"
            f"📚 {work.deadline.subject.name}\n"
            f"📝 {work_title}: {work.deadline.title}\n"
            f"📅 Дедлайн: {work.deadline.deadline_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Нажмите кнопку ниже, чтобы получить файл или подтвердить автоматическую отправку."
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Скачать", callback_data=f"work_download:{work.id}"),
                InlineKeyboardButton(text="✅ Подтвердить отправку", callback_data=f"work_confirm:{work.id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"work_regenerate:{work.id}")
            ]
        ])

        try:
            await self.bot.send_message(user.telegram_id, message, reply_markup=keyboard)
        except Exception as e:
            print(f"Failed to notify user {user.telegram_id}: {e}")

    async def check_and_send_works(self):
        """Проверяет и отправляет подтвержденные работы."""
        now = datetime.now(MOSCOW_TZ).replace(tzinfo=None)

        # Get confirmed works that should be sent
        result = await self.session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject).selectinload(Subject.user)
            )
            .where(
                and_(
                    GeneratedWork.status == "confirmed",
                    GeneratedWork.scheduled_send_at <= now
                )
            )
        )
        works_to_send = result.scalars().all()

        for work in works_to_send:
            try:
                user = work.deadline.subject.user
                await self._send_work(user, work)
            except Exception as e:
                print(f"Error sending work {work.id}: {e}")

        # Also check auto-send works (require_confirmation=False)
        result = await self.session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject).selectinload(Subject.user)
            )
            .where(
                and_(
                    GeneratedWork.status == "ready",
                    GeneratedWork.auto_send == True,
                    GeneratedWork.scheduled_send_at <= now
                )
            )
        )
        auto_send_works = result.scalars().all()

        for work in auto_send_works:
            try:
                user = work.deadline.subject.user
                await self._send_work(user, work)
            except Exception as e:
                print(f"Error auto-sending work {work.id}: {e}")

    async def _send_work(self, user: User, work: GeneratedWork):
        """Отправляет готовую работу пользователю в Telegram."""
        if not self.bot or not work.file_path:
            return

        from aiogram.types import FSInputFile

        work_type_name = {
            "homework": "Домашняя работа",
            "lab": "Лабораторная работа",
            "practical": "Практическая работа",
            "coursework": "Курсовая работа",
            "report": "Реферат",
        }.get(work.deadline.work_type, work.deadline.work_type)

        work_title = work_type_name
        if work.deadline.work_number:
            work_title += f" №{work.deadline.work_number}"

        caption = (
            f"📤 Готовая работа\n\n"
            f"📚 {work.deadline.subject.name}\n"
            f"📝 {work_title}: {work.deadline.title}\n"
            f"📅 Дедлайн: {work.deadline.deadline_date.strftime('%d.%m.%Y %H:%M')}"
        )

        try:
            document = FSInputFile(work.file_path, filename=work.file_name)
            await self.bot.send_document(user.telegram_id, document, caption=caption)

            work.status = "sent"
            work.sent_at = datetime.utcnow()
            await self.session.commit()

            print(f"Work {work.id} sent to user {user.telegram_id}")

        except Exception as e:
            print(f"Failed to send work {work.id}: {e}")
            raise

    async def send_work_reminders(self):
        """Отправляет напоминания о работах за N дней до дедлайна."""
        now = datetime.now(MOSCOW_TZ).replace(tzinfo=None)

        # Get all users with work settings
        result = await self.session.execute(
            select(User)
            .options(
                selectinload(User.work_settings),
                selectinload(User.subjects).selectinload(Subject.deadlines).selectinload(Deadline.generated_work)
            )
        )
        users = result.scalars().all()

        for user in users:
            settings = user.work_settings
            if not settings:
                continue

            reminder_days = settings.reminder_days_before or [3, 1]

            for subject in user.subjects:
                for deadline in subject.deadlines:
                    if deadline.is_completed:
                        continue

                    # Check if we should send reminder
                    for days in reminder_days:
                        reminder_threshold = deadline.deadline_date - timedelta(days=days)
                        # Check if we're within the reminder window (same day)
                        if (reminder_threshold.date() == now.date() and
                            not self._reminder_sent_today(deadline, days)):
                            await self._send_deadline_reminder(user, deadline, days)

    def _reminder_sent_today(self, deadline: Deadline, days: int) -> bool:
        """Проверяет, было ли уже отправлено напоминание сегодня."""
        # This is a simplified check - in production, you'd track this in DB
        return False

    async def _send_deadline_reminder(self, user: User, deadline: Deadline, days_left: int):
        """Отправляет напоминание о приближающемся дедлайне."""
        if not self.bot:
            return

        work_status = ""
        if deadline.generated_work:
            status_map = {
                "pending": "⏳ ожидает генерации",
                "generating": "🔄 генерируется",
                "ready": "✅ готова к отправке",
                "confirmed": "📤 подтверждена к отправке",
                "sent": "✅ отправлена"
            }
            work_status = f"\n📋 Статус работы: {status_map.get(deadline.generated_work.status, deadline.generated_work.status)}"

        message = (
            f"⏰ Напоминание о дедлайне!\n\n"
            f"📚 {deadline.subject.name}\n"
            f"📝 {deadline.title}\n"
            f"⏱ Осталось: {days_left} дн.\n"
            f"📅 Срок: {deadline.deadline_date.strftime('%d.%m.%Y %H:%M')}"
            f"{work_status}"
        )

        try:
            await self.bot.send_message(user.telegram_id, message)
        except Exception as e:
            print(f"Failed to send reminder to user {user.telegram_id}: {e}")
