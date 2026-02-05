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
from app.models import (
    User, Subject, Teacher, Deadline, Note, Material, ReminderSettings,
    TitleTemplate, GeneratedWork, UserWorkSettings
)
from app.services.gpt_service import GPTService
from app.services.reminder_service import ReminderService
from app.services.work_generator import WorkGeneratorService
from app.services.ical_sync_service import ICalSyncService

import os
import io

settings = get_settings()

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
gpt_service = GPTService()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "generated")
MATERIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "materials")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(MATERIALS_DIR, exist_ok=True)


class AddTeacherStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_name = State()
    waiting_for_role = State()


class ReminderSettingsStates(StatesGroup):
    waiting_for_hours = State()


class UploadMaterialStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_new_subject = State()
    waiting_for_file = State()


class UploadTemplateStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_file = State()


class GenerateWorkStates(StatesGroup):
    waiting_for_deadline = State()


class ScheduleUrlStates(StatesGroup):
    waiting_for_url = State()


WORK_TYPE_NAMES = {
    "homework": "Домашняя работа",
    "lab": "Лабораторная работа",
    "practical": "Практическая работа",
    "coursework": "Курсовая работа",
    "report": "Реферат",
    "essay": "Эссе",
    "presentation": "Презентация",
    "exam": "Экзамен",
    "test": "Контрольная работа",
}


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
        "**Основные команды:**\n"
        "/start - Начало работы\n"
        "/teachers - Список преподавателей\n"
        "/deadlines - Список дедлайнов\n"
        "/schedule - Показать расписание\n"
        "/add\\_teacher - Добавить преподавателя\n"
        "/upload - Загрузить материал\n"
        "/settings - Настройки напоминаний\n\n"
        "**Расписание:**\n"
        "/schedule\\_url - Указать ссылку на iCal расписание\n"
        "/sync - Синхронизировать расписание вручную\n\n"
        "**Работы и генерация:**\n"
        "/works - Список сгенерированных работ\n"
        "/generate - Сгенерировать работу вручную\n"
        "/templates - Шаблоны титульных листов\n"
        "/upload\\_template - Загрузить шаблон титульника\n"
        "/work\\_settings - Настройки автогенерации\n\n"
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


@dp.message(Command("schedule_url"))
async def cmd_schedule_url(message: Message, state: FSMContext):
    """Устанавливает URL для iCal расписания."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        current_url = db_user.ical_url if db_user else None

    if current_url:
        await state.set_state(ScheduleUrlStates.waiting_for_url)
        await message.answer(
            f"📅 Текущий URL расписания:\n`{current_url}`\n\n"
            "Отправь новый URL для iCal расписания (например, с сайта МИРЕА).\n"
            "Или отправь /cancel для отмены.",
            parse_mode="Markdown"
        )
    else:
        await state.set_state(ScheduleUrlStates.waiting_for_url)
        await message.answer(
            "📅 Отправь URL для iCal расписания.\n\n"
            "Например: `https://english.mirea.ru/schedule/api/ical/1/856`\n\n"
            "Ссылку можно получить на сайте расписания МИРЕА.",
            parse_mode="Markdown"
        )


@dp.message(ScheduleUrlStates.waiting_for_url)
async def process_schedule_url(message: Message, state: FSMContext):
    """Обрабатывает введённый URL расписания."""
    url = message.text.strip()

    # Basic URL validation
    if not url.startswith("http://") and not url.startswith("https://"):
        await message.answer("❌ Неверный формат URL. Ссылка должна начинаться с http:// или https://")
        return

    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()
        if db_user:
            db_user.ical_url = url
            await session.commit()

    await state.clear()
    await message.answer(
        f"✅ URL расписания сохранён!\n\n"
        f"Расписание будет синхронизироваться автоматически каждые 6 часов.\n"
        f"Для ручной синхронизации используй /sync",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("sync"))
async def cmd_sync(message: Message):
    """Синхронизирует расписание вручную."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one_or_none()

        if not db_user or not db_user.ical_url:
            await message.answer(
                "❌ URL расписания не настроен.\n"
                "Используй /schedule\\_url чтобы указать ссылку на iCal.",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return

        await message.answer("🔄 Синхронизация расписания...")
        await bot.send_chat_action(message.chat.id, "typing")

        sync_service = ICalSyncService(session)
        result = await sync_service.sync_user_schedule(db_user)

        if result["success"]:
            await message.answer(
                f"✅ Расписание синхронизировано!\n\n"
                f"📊 Событий в iCal: {result['events_parsed']}\n"
                f"📅 Уникальных занятий: {result['patterns_found']}\n"
                f"➕ Добавлено: {result['created']}\n"
                f"🔄 Обновлено: {result['updated']}",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                f"❌ Ошибка синхронизации: {result.get('error', 'Неизвестная ошибка')}",
                reply_markup=get_main_keyboard()
            )


@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    """Показывает расписание на сегодня/завтра."""
    user = await get_or_create_user(message.from_user.id)
    from datetime import date

    today = date.today()
    day_of_week = today.weekday()
    week_number = today.isocalendar()[1]
    week_type = "even" if week_number % 2 == 0 else "odd"

    days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    async with async_session() as session:
        # Get all subjects with schedule entries
        result = await session.execute(
            select(Subject)
            .options(selectinload(Subject.schedule_entries))
            .where(Subject.user_id == user.id)
        )
        subjects = result.scalars().all()

        if not subjects:
            await message.answer(
                "📅 Расписание пусто.\n\n"
                "Настрой iCal с помощью /schedule\\_url",
                parse_mode="Markdown",
                reply_markup=get_main_keyboard()
            )
            return

        # Collect entries for today
        today_entries = []
        for subject in subjects:
            for entry in subject.schedule_entries:
                if entry.day_of_week == day_of_week:
                    if entry.week_type == "both" or entry.week_type == week_type:
                        today_entries.append((subject.name, entry))

        # Sort by start time
        today_entries.sort(key=lambda x: x[1].start_time)

        week_text = "чётная" if week_type == "even" else "нечётная"
        text = f"📅 **Расписание на сегодня** ({days_ru[day_of_week]}, {week_text} неделя)\n\n"

        if not today_entries:
            text += "🎉 Сегодня занятий нет!"
        else:
            for subject_name, entry in today_entries:
                type_emoji = "📖" if entry.class_type == "lecture" else "📝" if entry.class_type == "practice" else "🔬"
                text += f"{type_emoji} **{entry.start_time}-{entry.end_time}** {subject_name}\n"
                if entry.room:
                    text += f"   📍 {entry.room}\n"
                if entry.teacher_name:
                    text += f"   👨‍🏫 {entry.teacher_name}\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


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
        await state.set_state(UploadMaterialStates.waiting_for_new_subject)
        await state.update_data(user_id=user.id)
        await message.answer(
            "У тебя пока нет предметов. Напиши название предмета, чтобы создать его:",
            reply_markup=get_main_keyboard()
        )
        return

    buttons = [
        [InlineKeyboardButton(text=s.name, callback_data=f"upload_subj_{s.id}")]
        for s in subjects
    ]
    buttons.append([InlineKeyboardButton(text="➕ Новый предмет", callback_data="upload_new_subj")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.set_state(UploadMaterialStates.waiting_for_subject)
    await message.answer(
        "Выбери предмет для загрузки материала:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "upload_new_subj")
async def process_upload_new_subject(callback: CallbackQuery, state: FSMContext):
    """Предлагает ввести название нового предмета."""
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    await state.update_data(user_id=user.id)
    await state.set_state(UploadMaterialStates.waiting_for_new_subject)
    await callback.message.answer("Напиши название нового предмета:")


@dp.message(UploadMaterialStates.waiting_for_new_subject)
async def process_new_subject_name(message: Message, state: FSMContext):
    """Создает новый предмет и переходит к загрузке файла."""
    data = await state.get_data()
    user_id = data.get("user_id")
    if not user_id:
        user = await get_or_create_user(message.from_user.id)
        user_id = user.id

    subject_name = message.text.strip()
    async with async_session() as session:
        subject = Subject(user_id=user_id, name=subject_name)
        session.add(subject)
        await session.commit()
        await session.refresh(subject)
        subject_id = subject.id

    await state.update_data(subject_id=subject_id)

    # If there's a pending file from direct send, process it now
    pending_file_id = data.get("pending_file_id")
    if pending_file_id:
        pending_file_name = data.get("pending_file_name", "file")
        file = await bot.get_file(pending_file_id)
        file_bytes = await bot.download_file(file.file_path)

        os.makedirs(MATERIALS_DIR, exist_ok=True)
        safe_name = f"{subject_id}_{pending_file_name}"
        save_path = os.path.join(MATERIALS_DIR, safe_name)

        with open(save_path, "wb") as f:
            f.write(file_bytes.read())

        file_ext = os.path.splitext(pending_file_name)[1].lower()
        async with async_session() as session:
            material = Material(
                subject_id=subject_id,
                file_name=pending_file_name,
                file_type=file_ext.replace(".", ""),
                file_path=save_path
            )
            session.add(material)
            await session.commit()

        await state.clear()

        # Detailed notification
        file_ext_clean = file_ext.replace(".", "")
        file_type_names = {
            'pdf': '📕 PDF документ',
            'docx': '📘 Word документ',
            'doc': '📘 Word документ',
            'xlsx': '📗 Excel таблица',
            'xls': '📗 Excel таблица',
            'txt': '📄 Текстовый файл',
        }
        file_type_label = file_type_names.get(file_ext_clean, '📁 Файл')

        text = f"✅ **Материал загружен!**\n\n"
        text += f"📚 **Создан предмет:** {subject_name}\n"
        text += f"{file_type_label}\n"
        text += f"📎 **Файл:** {pending_file_name}\n"
        text += f"\n💡 Теперь ты можешь загружать материалы к этому предмету через /upload"

        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        await state.set_state(UploadMaterialStates.waiting_for_file)
        await message.answer(f"Предмет «{subject_name}» создан. Теперь отправь файл (PDF, Excel, DOCX или TXT):")


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

    # Detailed notification
    file_type_names = {
        'pdf': '📕 PDF документ',
        'docx': '📘 Word документ',
        'doc': '📘 Word документ',
        'xlsx': '📗 Excel таблица',
        'xls': '📗 Excel таблица',
        'txt': '📄 Текстовый файл',
    }
    file_type_label = file_type_names.get(file_ext, '📁 Файл')

    text = f"✅ **Материал загружен!**\n\n"
    text += f"{file_type_label}\n"
    text += f"📎 **Файл:** {file_name}\n"
    text += f"📚 **Предмет:** {subject_name}\n"
    if parsed_text:
        text += f"📝 **Извлечено:** {len(parsed_text):,} символов текста\n"
        # Show preview of extracted text
        preview = parsed_text[:200].replace('\n', ' ').strip()
        if preview:
            text += f"\n💬 *Превью:* {preview}..."

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


# ============= GENERATED WORKS HANDLERS =============

@dp.message(Command("works"))
async def cmd_works(message: Message):
    """Показывает список сгенерированных работ."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject)
            )
            .where(Subject.user_id == user.id)
            .order_by(Deadline.deadline_date)
        )
        works = result.scalars().all()

    if not works:
        await message.answer(
            "📋 У тебя пока нет работ для генерации.\n\n"
            "Добавь дедлайн с типом работы (лабораторная, практическая и т.д.), "
            "и система автоматически подготовит работу к сроку сдачи!",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📋 **Твои работы:**\n\n"
    for work in works:
        status_emoji = {
            "pending": "⏳",
            "generating": "🔄",
            "ready": "✅",
            "confirmed": "📤",
            "sent": "✅"
        }.get(work.status, "❓")

        status_text = {
            "pending": "ожидает генерации",
            "generating": "генерируется",
            "ready": "готова",
            "confirmed": "подтверждена",
            "sent": "отправлена"
        }.get(work.status, work.status)

        work_type_name = WORK_TYPE_NAMES.get(work.deadline.work_type, work.deadline.work_type)
        work_title = work_type_name
        if work.deadline.work_number:
            work_title += f" №{work.deadline.work_number}"

        text += f"{status_emoji} **{work_title}**\n"
        text += f"   📚 {work.deadline.subject.name}\n"
        text += f"   📝 {work.deadline.title}\n"
        text += f"   📅 Дедлайн: {work.deadline.deadline_date.strftime('%d.%m.%Y')}\n"
        text += f"   📊 Статус: {status_text}\n"

        if work.status == "ready":
            text += f"   ⚡ /download\\_{work.id} — скачать\n"
            text += f"   ✅ /confirm\\_{work.id} — подтвердить отправку\n"

        text += "\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("generate"))
async def cmd_generate(message: Message, state: FSMContext):
    """Вручную запустить генерацию работы."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        # Get deadlines with pending works
        result = await session.execute(
            select(Deadline)
            .join(Subject)
            .options(
                selectinload(Deadline.subject),
                selectinload(Deadline.generated_work)
            )
            .where(Subject.user_id == user.id)
            .where(Deadline.is_completed == False)
            .order_by(Deadline.deadline_date)
        )
        deadlines = result.scalars().all()

    # Filter to deadlines with pending works
    pending_deadlines = [d for d in deadlines if d.generated_work and d.generated_work.status == "pending"]

    if not pending_deadlines:
        await message.answer(
            "Нет работ, ожидающих генерации.\n"
            "Добавь дедлайн с типом работы через приложение или заметку!",
            reply_markup=get_main_keyboard()
        )
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{WORK_TYPE_NAMES.get(d.work_type, d.work_type)} - {d.title[:20]}",
            callback_data=f"gen_work:{d.id}"
        )]
        for d in pending_deadlines[:10]  # Limit to 10
    ])

    await message.answer(
        "Выбери работу для генерации:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("gen_work:"))
async def callback_generate_work(callback: CallbackQuery):
    """Генерирует работу по запросу."""
    await callback.answer("Начинаю генерацию...")
    deadline_id = int(callback.data.split(":")[1])

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(
                selectinload(GeneratedWork.deadline).selectinload(Deadline.subject).selectinload(Subject.materials),
                selectinload(GeneratedWork.title_template)
            )
            .where(GeneratedWork.deadline_id == deadline_id, Subject.user_id == user.id)
        )
        work = result.scalar_one_or_none()

        if not work:
            await callback.message.answer("❌ Работа не найдена.")
            return

        if work.status != "pending":
            await callback.message.answer(f"Работа уже в статусе: {work.status}")
            return

        # Update status
        work.status = "generating"
        await session.commit()

        await callback.message.answer("🔄 Генерирую работу... Это может занять несколько минут.")

        try:
            # Collect materials
            materials_text = []
            for material in work.deadline.subject.materials:
                if material.parsed_text:
                    materials_text.append(f"=== {material.file_name} ===\n{material.parsed_text}")

            # Generate content
            generator = WorkGeneratorService(gpt_service)
            content = await generator.generate_work_content(
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
                template_result = await session.execute(
                    select(TitleTemplate).where(
                        TitleTemplate.user_id == user.id,
                        TitleTemplate.is_default == True
                    )
                )
                template = template_result.scalar_one_or_none()

            # Get user info
            user_result = await session.execute(select(User).where(User.id == user.id))
            user_data = user_result.scalar_one()

            # Create document
            file_name, file_path = await generator.create_document(
                content=content,
                subject_name=work.deadline.subject.name,
                work_type=work.deadline.work_type,
                work_number=work.deadline.work_number,
                student_name=user_data.first_name or "Студент",
                group_number=user_data.group_number or "",
                template_path=template.file_path if template else None,
                output_dir=GENERATED_DIR,
                user_id=user.id,
                deadline_id=work.deadline_id
            )

            work.content_text = content
            work.file_name = file_name
            work.file_path = file_path
            work.status = "ready"
            work.generated_at = datetime.now()
            await session.commit()

            # Send notification
            work_type_name = WORK_TYPE_NAMES.get(work.deadline.work_type, work.deadline.work_type)
            work_title = work_type_name
            if work.deadline.work_number:
                work_title += f" №{work.deadline.work_number}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 Скачать", callback_data=f"work_download:{work.id}"),
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"work_confirm:{work.id}")
                ],
                [
                    InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=f"work_regenerate:{work.id}")
                ]
            ])

            await callback.message.answer(
                f"✅ **Работа готова!**\n\n"
                f"📚 {work.deadline.subject.name}\n"
                f"📝 {work_title}: {work.deadline.title}\n"
                f"📅 Дедлайн: {work.deadline.deadline_date.strftime('%d.%m.%Y')}\n\n"
                "Выбери действие:",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        except Exception as e:
            work.status = "pending"
            await session.commit()
            await callback.message.answer(f"❌ Ошибка генерации: {str(e)}")


@dp.callback_query(F.data.startswith("work_download:"))
async def callback_download_work(callback: CallbackQuery):
    """Отправляет файл работы пользователю."""
    await callback.answer()
    work_id = int(callback.data.split(":")[1])

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(selectinload(GeneratedWork.deadline).selectinload(Deadline.subject))
            .where(GeneratedWork.id == work_id, Subject.user_id == user.id)
        )
        work = result.scalar_one_or_none()

    if not work or not work.file_path:
        await callback.message.answer("❌ Файл не найден.")
        return

    from aiogram.types import FSInputFile

    work_type_name = WORK_TYPE_NAMES.get(work.deadline.work_type, work.deadline.work_type)
    work_title = work_type_name
    if work.deadline.work_number:
        work_title += f" №{work.deadline.work_number}"

    try:
        document = FSInputFile(work.file_path, filename=work.file_name)
        await callback.message.answer_document(
            document,
            caption=f"📄 {work_title}\n📚 {work.deadline.subject.name}"
        )
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка отправки файла: {str(e)}")


@dp.callback_query(F.data.startswith("work_confirm:"))
async def callback_confirm_work(callback: CallbackQuery):
    """Подтверждает отправку работы."""
    await callback.answer()
    work_id = int(callback.data.split(":")[1])

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .options(selectinload(GeneratedWork.deadline).selectinload(Deadline.subject))
            .where(GeneratedWork.id == work_id, Subject.user_id == user.id)
        )
        work = result.scalar_one_or_none()

        if not work:
            await callback.message.answer("❌ Работа не найдена.")
            return

        if work.status != "ready":
            await callback.message.answer(f"Работа не готова к подтверждению (статус: {work.status})")
            return

        work.status = "confirmed"
        work.confirmed_at = datetime.now()
        await session.commit()

    await callback.message.answer(
        f"✅ Работа подтверждена к отправке!\n\n"
        f"Она будет автоматически отправлена "
        f"{'в запланированное время' if work.scheduled_send_at else 'в ближайшее время'}."
    )


@dp.callback_query(F.data.startswith("work_regenerate:"))
async def callback_regenerate_work(callback: CallbackQuery):
    """Перегенерирует работу."""
    await callback.answer()
    work_id = int(callback.data.split(":")[1])

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(GeneratedWork)
            .join(Deadline)
            .join(Subject)
            .where(GeneratedWork.id == work_id, Subject.user_id == user.id)
        )
        work = result.scalar_one_or_none()

        if not work:
            await callback.message.answer("❌ Работа не найдена.")
            return

        # Delete old file
        if work.file_path and os.path.exists(work.file_path):
            os.remove(work.file_path)

        # Reset status
        work.status = "pending"
        work.file_name = None
        work.file_path = None
        work.content_text = None
        work.generated_at = None
        await session.commit()

    await callback.message.answer(
        "🔄 Работа сброшена для перегенерации.\n"
        "Используй /generate чтобы запустить генерацию заново."
    )


# ============= TITLE TEMPLATES HANDLERS =============

@dp.message(Command("templates"))
async def cmd_templates(message: Message):
    """Показывает шаблоны титульных листов."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(TitleTemplate)
            .where(TitleTemplate.user_id == user.id)
            .order_by(TitleTemplate.is_default.desc(), TitleTemplate.created_at.desc())
        )
        templates = result.scalars().all()

    if not templates:
        await message.answer(
            "📄 У тебя пока нет шаблонов титульных листов.\n\n"
            "Загрузи шаблон через /upload\\_template\n\n"
            "**Поддерживаемые плейсхолдеры:**\n"
            "• `{{subject_name}}` — название предмета\n"
            "• `{{date}}` — дата выполнения\n"
            "• `{{work_type}}` — тип работы\n"
            "• `{{work_number}}` — номер работы\n"
            "• `{{student_name}}` — имя студента\n"
            "• `{{group_number}}` — номер группы",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📄 **Твои шаблоны титульных листов:**\n\n"
    for t in templates:
        default_mark = " ⭐ (по умолчанию)" if t.is_default else ""
        text += f"• **{t.name}**{default_mark}\n"
        text += f"   Файл: {t.file_name}\n\n"

    text += "\n/upload\\_template — загрузить новый шаблон"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("upload_template"))
async def cmd_upload_template(message: Message, state: FSMContext):
    """Начинает процесс загрузки шаблона титульного листа."""
    await state.set_state(UploadTemplateStates.waiting_for_name)
    await message.answer(
        "Введи название для шаблона (например, «Основной шаблон»):"
    )


@dp.message(UploadTemplateStates.waiting_for_name)
async def process_template_name(message: Message, state: FSMContext):
    """Обрабатывает название шаблона."""
    await state.update_data(template_name=message.text)
    await state.set_state(UploadTemplateStates.waiting_for_file)
    await message.answer(
        "Теперь отправь DOCX файл шаблона.\n\n"
        "**Используй плейсхолдеры в шаблоне:**\n"
        "• `{{subject_name}}` — название предмета\n"
        "• `{{date}}` — дата выполнения\n"
        "• `{{work_type}}` — тип работы\n"
        "• `{{work_number}}` — номер работы\n"
        "• `{{student_name}}` — имя студента\n"
        "• `{{group_number}}` — номер группы",
        parse_mode="Markdown"
    )


@dp.message(UploadTemplateStates.waiting_for_file, F.document)
async def process_template_file(message: Message, state: FSMContext):
    """Обрабатывает загруженный шаблон."""
    data = await state.get_data()
    template_name = data.get('template_name', 'Шаблон')

    document = message.document
    file_name = document.file_name or "template.docx"

    if not file_name.endswith(".docx"):
        await message.answer(
            "❌ Шаблон должен быть в формате DOCX.",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        return

    user = await get_or_create_user(message.from_user.id)

    # Download file
    file = await bot.get_file(document.file_id)
    file_content = await bot.download_file(file.file_path)
    content = file_content.read()

    # Save to disk
    file_path = os.path.join(TEMPLATES_DIR, f"{user.id}_{datetime.now().timestamp()}_{file_name}")
    with open(file_path, "wb") as f:
        f.write(content)

    async with async_session() as session:
        # Check if this is the first template (make it default)
        result = await session.execute(
            select(TitleTemplate).where(TitleTemplate.user_id == user.id)
        )
        existing = result.scalars().all()
        is_default = len(existing) == 0

        template = TitleTemplate(
            user_id=user.id,
            name=template_name,
            file_name=file_name,
            file_path=file_path,
            is_default=is_default
        )
        session.add(template)
        await session.commit()

    await state.clear()

    default_text = " и установлен по умолчанию" if is_default else ""
    await message.answer(
        f"✅ Шаблон **{template_name}** загружен{default_text}!\n\n"
        "Теперь он будет использоваться при генерации работ.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# ============= WORK SETTINGS HANDLERS =============

@dp.message(Command("work_settings"))
async def cmd_work_settings(message: Message):
    """Показывает настройки автогенерации работ."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(UserWorkSettings).where(UserWorkSettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()

    if not settings:
        reminder_days = [3, 1]
        auto_generate = True
        generate_days = 5
        require_confirm = True
        send_days = 1
    else:
        reminder_days = settings.reminder_days_before
        auto_generate = settings.auto_generate
        generate_days = settings.generate_days_before
        require_confirm = settings.require_confirmation
        send_days = settings.default_send_days_before

    text = (
        "⚙️ **Настройки автогенерации работ:**\n\n"
        f"📅 Напоминания за: {', '.join(str(d) + ' дн.' for d in reminder_days)}\n"
        f"🤖 Автогенерация: {'✅ Вкл' if auto_generate else '❌ Выкл'}\n"
        f"⏰ Генерировать за: {generate_days} дн. до дедлайна\n"
        f"✅ Требовать подтверждение: {'Да' if require_confirm else 'Нет'}\n"
        f"📤 Отправлять за: {send_days} дн. до дедлайна\n\n"
        "Для изменения настроек используй приложение."
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


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
        await state.update_data(user_id=user.id,
                               pending_file_id=message.document.file_id,
                               pending_file_name=message.document.file_name)
        await state.set_state(UploadMaterialStates.waiting_for_new_subject)
        await message.answer(
            "У тебя пока нет предметов. Напиши название предмета, чтобы создать его и загрузить файл:",
            reply_markup=get_main_keyboard()
        )
        return

    # Ask which subject
    buttons = [
        [InlineKeyboardButton(text=s.name, callback_data=f"upload_subj_{s.id}")]
        for s in subjects
    ]
    buttons.append([InlineKeyboardButton(text="➕ Новый предмет", callback_data="upload_new_subj")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

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
            if parsed_data.get("error"):
                response_text += "⚠️ Не удалось обработать заметку через AI (проверь OPENAI_API_KEY в .env).\n"
                response_text += "Заметка сохранена как есть.\n"
            else:
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
