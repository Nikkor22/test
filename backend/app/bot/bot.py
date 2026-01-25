from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.base import async_session
from app.models import User, Subject, Teacher, Deadline, Note, ReminderSettings
from app.services.gpt_service import GPTService
from app.services.reminder_service import ReminderService

settings = get_settings()

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
gpt_service = GPTService()


class AddTeacherStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_name = State()


class ReminderSettingsStates(StatesGroup):
    waiting_for_hours = State()


def get_main_keyboard():
    """Главная клавиатура с кнопкой WebApp."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📚 Открыть приложение",
            web_app=WebAppInfo(url=settings.webapp_url)
        )],
        [
            InlineKeyboardButton(text="👨‍🏫 Преподаватели", callback_data="teachers"),
            InlineKeyboardButton(text="📅 Дедлайны", callback_data="deadlines")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки напоминаний", callback_data="reminder_settings")]
    ])


async def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None) -> User:
    """Получает или создает пользователя."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name
            )
            session.add(user)
            await session.flush()  # Получаем ID пользователя

            # Создаем дефолтные настройки напоминаний
            reminder_settings = ReminderSettings(
                user_id=user.id,
                hours_before=[72, 24, 12]  # 3 дня, 1 день, 12 часов
            )
            session.add(reminder_settings)

            await session.commit()
            await session.refresh(user)

        return user


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я помогу тебе отслеживать информацию о преподавателях и дедлайнах.\n\n"
        "📝 **Как использовать:**\n"
        "• Просто пиши мне заметки о преподавателях и дедлайнах\n"
        "• Я автоматически извлеку и сохраню важную информацию\n"
        "• Открой приложение для просмотра всех данных\n\n"
        "**Примеры заметок:**\n"
        "• «Петров по матану строгий, любит теорию»\n"
        "• «Контрольная по физике 15 февраля»\n"
        "• «Лабораторная работа №3 по программированию сдать до 20.02»",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    await message.answer(
        "📖 **Справка**\n\n"
        "**Команды:**\n"
        "/start - Начало работы\n"
        "/teachers - Список преподавателей\n"
        "/deadlines - Список дедлайнов\n"
        "/add_teacher - Добавить преподавателя\n"
        "/settings - Настройки напоминаний\n\n"
        "**Заметки:**\n"
        "Просто пиши мне сообщения с информацией о преподавателях или дедлайнах.\n"
        "Я автоматически распознаю и сохраню данные.\n\n"
        "**Примеры:**\n"
        "• «Иванов по истории добрый, ставит автоматы»\n"
        "• «Экзамен по БД 25 января в 10:00»\n"
        "• «Курсовая по экономике до конца месяца, тема - инфляция»",
        parse_mode="Markdown"
    )


@dp.message(Command("teachers"))
async def cmd_teachers(message: Message):
    """Показывает список преподавателей."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Subject)
            .options(selectinload(Subject.teacher))
            .where(Subject.user_id == user.id)
        )
        subjects = result.scalars().all()

    if not subjects:
        await message.answer(
            "У тебя пока нет добавленных преподавателей.\n"
            "Напиши мне заметку о преподавателе, и я добавлю его автоматически!",
            reply_markup=get_main_keyboard()
        )
        return

    text = "👨‍🏫 **Твои преподаватели:**\n\n"
    for subject in subjects:
        if subject.teacher:
            text += f"📚 **{subject.name}**\n"
            text += f"   👤 {subject.teacher.name}\n"
            if subject.teacher.temperament:
                text += f"   🎭 {subject.teacher.temperament}\n"
            if subject.teacher.preferences:
                text += f"   💡 {subject.teacher.preferences}\n"
            text += "\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("deadlines"))
async def cmd_deadlines(message: Message):
    """Показывает список дедлайнов."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Deadline)
            .options(selectinload(Deadline.subject))
            .join(Subject)
            .where(Subject.user_id == user.id)
            .where(Deadline.is_completed == False)
            .order_by(Deadline.deadline_date)
        )
        deadlines = result.scalars().all()

    if not deadlines:
        await message.answer(
            "У тебя пока нет активных дедлайнов.\n"
            "Напиши мне о предстоящих работах!",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📅 **Твои дедлайны:**\n\n"
    for deadline in deadlines:
        date_str = deadline.deadline_date.strftime("%d.%m.%Y %H:%M")
        days_left = (deadline.deadline_date - datetime.now()).days

        emoji = "🟢" if days_left > 7 else "🟡" if days_left > 2 else "🔴"

        text += f"{emoji} **{deadline.title}**\n"
        text += f"   📚 {deadline.subject.name}\n"
        text += f"   📝 {deadline.work_type}\n"
        text += f"   ⏰ {date_str}"
        if days_left >= 0:
            text += f" (осталось {days_left} дн.)\n"
        else:
            text += " ⚠️ ПРОСРОЧЕНО\n"
        text += "\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("add_teacher"))
async def cmd_add_teacher(message: Message, state: FSMContext):
    """Начинает процесс добавления преподавателя."""
    await state.set_state(AddTeacherStates.waiting_for_subject)
    await message.answer(
        "Введи название предмета:",
        parse_mode="Markdown"
    )


@dp.message(AddTeacherStates.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    """Обрабатывает название предмета."""
    await state.update_data(subject_name=message.text)
    await state.set_state(AddTeacherStates.waiting_for_name)
    await message.answer("Введи имя преподавателя:")


@dp.message(AddTeacherStates.waiting_for_name)
async def process_teacher_name(message: Message, state: FSMContext):
    """Обрабатывает имя преподавателя."""
    data = await state.get_data()
    subject_name = data['subject_name']
    teacher_name = message.text

    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        # Создаем или находим предмет
        result = await session.execute(
            select(Subject).where(
                Subject.user_id == user.id,
                Subject.name == subject_name
            )
        )
        subject = result.scalar_one_or_none()

        if not subject:
            subject = Subject(user_id=user.id, name=subject_name)
            session.add(subject)
            await session.flush()

        # Создаем или обновляем преподавателя
        result = await session.execute(
            select(Teacher).where(Teacher.subject_id == subject.id)
        )
        teacher = result.scalar_one_or_none()

        if teacher:
            teacher.name = teacher_name
        else:
            teacher = Teacher(subject_id=subject.id, name=teacher_name)
            session.add(teacher)

        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Преподаватель **{teacher_name}** добавлен к предмету **{subject_name}**!\n\n"
        "Теперь можешь писать заметки о нём, и я буду дополнять профиль.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Настройки напоминаний."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()

    current = settings.hours_before if settings else [72, 24, 12]
    current_str = ", ".join([f"{h}ч" for h in current])

    await state.set_state(ReminderSettingsStates.waiting_for_hours)
    await message.answer(
        f"⚙️ **Настройки напоминаний**\n\n"
        f"Текущие напоминания: {current_str}\n\n"
        "Введи через запятую за сколько часов до дедлайна напоминать.\n"
        "Например: `72, 24, 12` (за 3 дня, за день, за 12 часов)",
        parse_mode="Markdown"
    )


@dp.message(ReminderSettingsStates.waiting_for_hours)
async def process_reminder_settings(message: Message, state: FSMContext):
    """Обрабатывает настройки напоминаний."""
    try:
        hours = [int(h.strip()) for h in message.text.split(",")]
        hours = sorted(hours, reverse=True)  # Сортируем по убыванию
    except ValueError:
        await message.answer("❌ Неверный формат. Введи числа через запятую, например: 72, 24, 12")
        return

    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        reminder_service = ReminderService(session)
        await reminder_service.update_user_settings(user.id, hours)

    await state.clear()

    hours_str = ", ".join([f"{h}ч" for h in hours])
    await message.answer(
        f"✅ Настройки сохранены!\n"
        f"Напоминания будут приходить за: {hours_str} до дедлайна.",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "teachers")
async def callback_teachers(callback: CallbackQuery):
    """Обработчик кнопки преподавателей."""
    await callback.answer()
    await cmd_teachers(callback.message)


@dp.callback_query(F.data == "deadlines")
async def callback_deadlines(callback: CallbackQuery):
    """Обработчик кнопки дедлайнов."""
    await callback.answer()
    await cmd_deadlines(callback.message)


@dp.callback_query(F.data == "reminder_settings")
async def callback_reminder_settings(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки настроек."""
    await callback.answer()
    # Создаем фейковое сообщение с нужным from_user
    await cmd_settings(callback.message, state)


@dp.message(F.text)
async def process_note(message: Message):
    """Обрабатывает текстовые заметки пользователя."""
    user = await get_or_create_user(message.from_user.id)

    # Отправляем индикатор "печатает"
    await bot.send_chat_action(message.chat.id, "typing")

    # Парсим заметку с помощью GPT
    parsed_data = await gpt_service.parse_note(message.text)

    async with async_session() as session:
        # Сохраняем заметку
        note = Note(
            user_id=user.id,
            raw_text=message.text,
            parsed_data=parsed_data,
            is_processed=True
        )
        session.add(note)

        response_text = "📝 Заметка сохранена!\n\n"

        # Обрабатываем информацию о преподавателе
        if parsed_data.get("teacher"):
            teacher_data = parsed_data["teacher"]
            subject_name = teacher_data.get("subject", "Неизвестный предмет")

            # Находим или создаем предмет
            result = await session.execute(
                select(Subject).where(
                    Subject.user_id == user.id,
                    Subject.name == subject_name
                )
            )
            subject = result.scalar_one_or_none()

            if not subject:
                subject = Subject(user_id=user.id, name=subject_name)
                session.add(subject)
                await session.flush()

            # Находим или создаем преподавателя
            result = await session.execute(
                select(Teacher).where(Teacher.subject_id == subject.id)
            )
            teacher = result.scalar_one_or_none()

            if teacher:
                # Обновляем существующего преподавателя
                if teacher_data.get("name"):
                    teacher.name = teacher_data["name"]
                if teacher_data.get("temperament"):
                    teacher.temperament = teacher_data["temperament"]
                if teacher_data.get("preferences"):
                    if teacher.preferences:
                        teacher.preferences += f"\n{teacher_data['preferences']}"
                    else:
                        teacher.preferences = teacher_data["preferences"]
                if teacher_data.get("notes"):
                    if teacher.notes:
                        teacher.notes += f"\n{teacher_data['notes']}"
                    else:
                        teacher.notes = teacher_data["notes"]
            else:
                teacher = Teacher(
                    subject_id=subject.id,
                    name=teacher_data.get("name", "Неизвестно"),
                    temperament=teacher_data.get("temperament"),
                    preferences=teacher_data.get("preferences"),
                    notes=teacher_data.get("notes")
                )
                session.add(teacher)

            response_text += f"👨‍🏫 Информация о преподавателе **{teacher.name}** ({subject_name}) обновлена\n"

        # Обрабатываем информацию о дедлайне
        if parsed_data.get("deadline"):
            deadline_data = parsed_data["deadline"]
            subject_name = deadline_data.get("subject", "Неизвестный предмет")

            # Находим или создаем предмет
            result = await session.execute(
                select(Subject).where(
                    Subject.user_id == user.id,
                    Subject.name == subject_name
                )
            )
            subject = result.scalar_one_or_none()

            if not subject:
                subject = Subject(user_id=user.id, name=subject_name)
                session.add(subject)
                await session.flush()

            # Парсим дату
            try:
                deadline_date = datetime.strptime(
                    deadline_data.get("deadline_date", ""),
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                deadline_date = datetime.now()

            # Создаем дедлайн
            deadline = Deadline(
                subject_id=subject.id,
                title=deadline_data.get("title", "Работа"),
                work_type=deadline_data.get("work_type", "Неизвестно"),
                description=deadline_data.get("description"),
                deadline_date=deadline_date
            )
            session.add(deadline)
            await session.flush()

            # Создаем напоминания
            reminder_service = ReminderService(session)
            await reminder_service.create_reminders_for_deadline(deadline, user.id)

            date_str = deadline_date.strftime("%d.%m.%Y %H:%M")
            response_text += f"📅 Дедлайн добавлен: **{deadline.title}** ({deadline.work_type}) - {date_str}\n"

        await session.commit()

        if not parsed_data.get("teacher") and not parsed_data.get("deadline"):
            response_text += "ℹ️ Не удалось извлечь информацию о преподавателе или дедлайне.\n"
            response_text += "Попробуй написать более конкретно, например:\n"
            response_text += "• «Петров по матану строгий»\n"
            response_text += "• «Контрольная по физике 15 февраля»"

    await message.answer(response_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def setup_bot():
    """Настройка бота."""
    pass
