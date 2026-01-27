from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.base import async_session
from app.models import User, Subject, Teacher, Deadline, Note, Material, ReminderSettings
from app.services.gpt_service import GPTService
from app.services.reminder_service import ReminderService

import os
import io

settings = get_settings()

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
gpt_service = GPTService()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class AddTeacherStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_name = State()
    waiting_for_role = State()


class ReminderSettingsStates(StatesGroup):
    waiting_for_hours = State()


class UploadMaterialStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_file = State()


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
        [
            InlineKeyboardButton(text="📎 Загрузить материал", callback_data="upload_material"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="reminder_settings")
        ]
    ])


def get_role_keyboard():
    """Клавиатура выбора роли преподавателя."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📖 Лектор", callback_data="role_lecturer"),
            InlineKeyboardButton(text="📝 Практикант", callback_data="role_practitioner")
        ]
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
            await session.flush()

            reminder_settings = ReminderSettings(
                user_id=user.id,
                hours_before=[72, 24, 12]
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
        "• Отправляй файлы (PDF, Excel, DOCX) для загрузки материалов\n"
        "• Открой приложение для просмотра расписания и данных\n\n"
        "**Примеры заметок:**\n"
        "• «Петров по матану строгий, любит теорию — лектор»\n"
        "• «Практикант по физике Сидорова, лояльная»\n"
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
        "/add\\_teacher - Добавить преподавателя\n"
        "/upload - Загрузить материал\n"
        "/settings - Настройки напоминаний\n\n"
        "**Заметки:**\n"
        "Просто пиши мне сообщения с информацией о преподавателях или дедлайнах.\n"
        "Я автоматически распознаю и сохраню данные.\n\n"
        "**Файлы:**\n"
        "Отправь PDF, Excel, DOCX или TXT файл — я сохраню его как материал.\n\n"
        "**Примеры:**\n"
        "• «Иванов по истории добрый, ставит автоматы — лектор»\n"
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
            .options(selectinload(Subject.teachers))
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
        if subject.teachers:
            text += f"📚 **{subject.name}**\n"
            for teacher in subject.teachers:
                role_emoji = "📖" if teacher.role == "lecturer" else "📝"
                role_text = "Лектор" if teacher.role == "lecturer" else "Практикант"
                text += f"   {role_emoji} {teacher.name} ({role_text})\n"
                if teacher.temperament:
                    text += f"      🎭 {teacher.temperament}\n"
                if teacher.preferences:
                    text += f"      💡 {teacher.preferences}\n"
                if teacher.peculiarities:
                    text += f"      ⚡ {teacher.peculiarities}\n"
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
        if deadline.gpt_description:
            text += f"   💡 {deadline.gpt_description[:100]}...\n"
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
    await state.update_data(teacher_name=message.text)
    await state.set_state(AddTeacherStates.waiting_for_role)
    await message.answer(
        "Выбери роль преподавателя:",
        reply_markup=get_role_keyboard()
    )


@dp.callback_query(F.data.startswith("role_"))
async def process_teacher_role(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор роли преподавателя."""
    await callback.answer()
    role = callback.data.replace("role_", "")
    data = await state.get_data()
    subject_name = data.get('subject_name')
    teacher_name = data.get('teacher_name')

    if not subject_name or not teacher_name:
        await callback.message.answer("Ошибка. Начни заново с /add_teacher")
        await state.clear()
        return

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
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

        teacher = Teacher(
            subject_id=subject.id,
            name=teacher_name,
            role=role
        )
        session.add(teacher)
        await session.commit()

    await state.clear()
    role_text = "Лектор" if role == "lecturer" else "Практикант"
    await callback.message.answer(
        f"✅ Преподаватель **{teacher_name}** ({role_text}) добавлен к предмету **{subject_name}**!\n\n"
        "Теперь можешь писать заметки о нём, и я буду дополнять профиль.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext):
    """Начинает процесс загрузки материала."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Subject).where(Subject.user_id == user.id)
        )
        subjects = result.scalars().all()

    if not subjects:
        await message.answer(
            "У тебя пока нет предметов. Сначала добавь преподавателя или напиши заметку!",
            reply_markup=get_main_keyboard()
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s.name, callback_data=f"upload_subj_{s.id}")]
        for s in subjects
    ])

    await state.set_state(UploadMaterialStates.waiting_for_subject)
    await message.answer(
        "Выбери предмет для загрузки материала:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("upload_subj_"))
async def process_upload_subject(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор предмета для загрузки."""
    await callback.answer()
    subject_id = int(callback.data.replace("upload_subj_", ""))
    await state.update_data(subject_id=subject_id)
    await state.set_state(UploadMaterialStates.waiting_for_file)
    await callback.message.answer(
        "Отправь файл (PDF, Excel, DOCX или TXT):"
    )


@dp.message(UploadMaterialStates.waiting_for_file, F.document)
async def process_upload_file(message: Message, state: FSMContext):
    """Обрабатывает загруженный файл."""
    data = await state.get_data()
    subject_id = data.get('subject_id')

    if not subject_id:
        await message.answer("Ошибка. Начни заново с /upload")
        await state.clear()
        return

    user = await get_or_create_user(message.from_user.id)
    document = message.document
    file_name = document.file_name or "unknown"
    file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "unknown"

    if file_ext not in ("pdf", "xlsx", "xls", "docx", "txt"):
        await message.answer(
            "❌ Неподдерживаемый формат файла. Поддерживаются: PDF, Excel, DOCX, TXT",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    await bot.send_chat_action(message.chat.id, "typing")

    # Download file
    file = await bot.get_file(document.file_id)
    file_content = await bot.download_file(file.file_path)
    content = file_content.read()

    # Save to disk
    file_path = os.path.join(UPLOAD_DIR, f"{user.id}_{subject_id}_{file_name}")
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse text
    parsed_text = await parse_file_content(file_ext, content)

    async with async_session() as session:
        result = await session.execute(
            select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id)
        )
        subject = result.scalar_one_or_none()
        if not subject:
            await message.answer("❌ Предмет не найден.")
            await state.clear()
            return

        material = Material(
            subject_id=subject_id,
            file_name=file_name,
            file_type=file_ext,
            file_path=file_path,
            parsed_text=parsed_text
        )
        session.add(material)
        await session.commit()

        subject_name = subject.name

    await state.clear()
    text = f"✅ Файл **{file_name}** загружен к предмету **{subject_name}**!"
    if parsed_text:
        text += f"\n📄 Извлечено {len(parsed_text)} символов текста."
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Настройки напоминаний."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user.id)
        )
        reminder_settings = result.scalar_one_or_none()

    current = reminder_settings.hours_before if reminder_settings else [72, 24, 12]
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
        hours = sorted(hours, reverse=True)
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
    await cmd_settings(callback.message, state)


@dp.callback_query(F.data == "upload_material")
async def callback_upload_material(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки загрузки материала."""
    await callback.answer()
    await cmd_upload(callback.message, state)


# Handle file uploads outside of state (direct sends)
@dp.message(F.document)
async def handle_document(message: Message, state: FSMContext):
    """Обрабатывает файлы, отправленные напрямую."""
    current_state = await state.get_state()
    if current_state == UploadMaterialStates.waiting_for_file:
        return  # Already handled by process_upload_file

    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Subject).where(Subject.user_id == user.id)
        )
        subjects = result.scalars().all()

    if not subjects:
        await message.answer(
            "У тебя пока нет предметов. Сначала добавь преподавателя или напиши заметку!\n"
            "После этого ты сможешь загружать файлы.",
            reply_markup=get_main_keyboard()
        )
        return

    # Ask which subject
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=s.name, callback_data=f"upload_subj_{s.id}")]
        for s in subjects
    ])

    # Store document info for later
    await state.update_data(pending_file_id=message.document.file_id,
                           pending_file_name=message.document.file_name)
    await state.set_state(UploadMaterialStates.waiting_for_subject)
    await message.answer(
        "Выбери предмет для загрузки этого файла:",
        reply_markup=keyboard
    )


@dp.message(F.text)
async def process_note(message: Message):
    """Обрабатывает текстовые заметки пользователя."""
    user = await get_or_create_user(message.from_user.id)

    await bot.send_chat_action(message.chat.id, "typing")

    parsed_data = await gpt_service.parse_note(message.text)

    async with async_session() as session:
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
            role = teacher_data.get("role", "lecturer")

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

            # Find teacher by subject and role
            result = await session.execute(
                select(Teacher).where(
                    Teacher.subject_id == subject.id,
                    Teacher.role == role
                )
            )
            teacher = result.scalar_one_or_none()

            if teacher:
                if teacher_data.get("name"):
                    teacher.name = teacher_data["name"]
                if teacher_data.get("temperament"):
                    teacher.temperament = teacher_data["temperament"]
                if teacher_data.get("preferences"):
                    if teacher.preferences:
                        teacher.preferences += f"\n{teacher_data['preferences']}"
                    else:
                        teacher.preferences = teacher_data["preferences"]
                if teacher_data.get("peculiarities"):
                    if teacher.peculiarities:
                        teacher.peculiarities += f"\n{teacher_data['peculiarities']}"
                    else:
                        teacher.peculiarities = teacher_data["peculiarities"]
                if teacher_data.get("notes"):
                    if teacher.notes:
                        teacher.notes += f"\n{teacher_data['notes']}"
                    else:
                        teacher.notes = teacher_data["notes"]
            else:
                teacher = Teacher(
                    subject_id=subject.id,
                    name=teacher_data.get("name", "Неизвестно"),
                    role=role,
                    temperament=teacher_data.get("temperament"),
                    preferences=teacher_data.get("preferences"),
                    peculiarities=teacher_data.get("peculiarities"),
                    notes=teacher_data.get("notes")
                )
                session.add(teacher)

            role_text = "Лектор" if role == "lecturer" else "Практикант"
            response_text += f"👨‍🏫 Информация о преподавателе **{teacher.name}** ({role_text}, {subject_name}) обновлена\n"

        # Обрабатываем информацию о дедлайне
        if parsed_data.get("deadline"):
            deadline_data = parsed_data["deadline"]
            subject_name = deadline_data.get("subject", "Неизвестный предмет")

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

            try:
                deadline_date = datetime.strptime(
                    deadline_data.get("deadline_date", ""),
                    "%Y-%m-%d %H:%M"
                )
            except ValueError:
                deadline_date = datetime.now()

            deadline = Deadline(
                subject_id=subject.id,
                title=deadline_data.get("title", "Работа"),
                work_type=deadline_data.get("work_type", "Неизвестно"),
                description=deadline_data.get("description"),
                deadline_date=deadline_date
            )
            session.add(deadline)
            await session.flush()

            # Generate GPT description
            try:
                teachers_result = await session.execute(
                    select(Teacher).where(Teacher.subject_id == subject.id)
                )
                teachers = teachers_result.scalars().all()
                teacher_info = None
                if teachers:
                    t = teachers[0]
                    teacher_info = {
                        "name": t.name, "role": t.role,
                        "temperament": t.temperament,
                        "preferences": t.preferences
                    }

                gpt_desc = await gpt_service.generate_deadline_description(
                    {"subject": subject.name, "title": deadline.title,
                     "work_type": deadline.work_type,
                     "description": deadline.description or "",
                     "deadline_date": deadline_date.strftime("%d.%m.%Y %H:%M")},
                    teacher_info
                )
                if gpt_desc:
                    deadline.gpt_description = gpt_desc
            except Exception as e:
                print(f"GPT description error in bot: {e}")

            # Создаем напоминания
            reminder_service = ReminderService(session)
            await reminder_service.create_reminders_for_deadline(deadline, user.id)

            date_str = deadline_date.strftime("%d.%m.%Y %H:%M")
            response_text += f"📅 Дедлайн добавлен: **{deadline.title}** ({deadline.work_type}) - {date_str}\n"
            if deadline.gpt_description:
                response_text += f"💡 {deadline.gpt_description[:150]}\n"

        await session.commit()

        if not parsed_data.get("teacher") and not parsed_data.get("deadline"):
            response_text += "ℹ️ Не удалось извлечь информацию о преподавателе или дедлайне.\n"
            response_text += "Попробуй написать более конкретно, например:\n"
            response_text += "• «Петров по матану строгий — лектор»\n"
            response_text += "• «Контрольная по физике 15 февраля»"

    await message.answer(response_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


async def parse_file_content(file_ext: str, content: bytes) -> str:
    """Parse text content from uploaded files."""
    try:
        if file_ext == "txt":
            return content.decode("utf-8", errors="ignore")

        elif file_ext == "pdf":
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "[PDF parsing requires PyPDF2]"

        elif file_ext in ("xlsx", "xls"):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(content))
                text = ""
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                        if row_text.strip(" |"):
                            text += row_text + "\n"
                return text
            except ImportError:
                return "[Excel parsing requires openpyxl]"

        elif file_ext == "docx":
            try:
                import docx
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join(p.text for p in doc.paragraphs)
                return text
            except ImportError:
                return "[DOCX parsing requires python-docx]"

    except Exception as e:
        return f"[Error parsing file: {e}]"

    return ""


async def setup_bot():
    """Настройка бота."""
    pass
