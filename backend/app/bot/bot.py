from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Document
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json

from app.config import get_settings
from app.models.base import async_session
from app.models import User, Subject, Teacher, SubjectTeacher, Deadline, Note, ReminderSettings, SemesterMaterial
from app.services.gpt_service import GPTService
from app.services.reminder_service import ReminderService

settings = get_settings()

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
gpt_service = GPTService()


class AddTeacherStates(StatesGroup):
    waiting_for_subject = State()
    waiting_for_name = State()
    waiting_for_role = State()


class ReminderSettingsStates(StatesGroup):
    waiting_for_hours = State()


class SemesterUploadStates(StatesGroup):
    waiting_for_data = State()


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
            InlineKeyboardButton(text="📤 Загрузить семестр", callback_data="upload_semester"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="reminder_settings")
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
    await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я помогу тебе с учёбой:\n"
        "• Отслеживать дедлайны и расписание\n"
        "• Хранить заметки о преподавателях\n"
        "• Напоминать о важных событиях\n"
        "• Делать AI-выжимки по предметам\n\n"
        "📤 **Загрузи данные семестра** — отправь файл или текст с расписанием\n"
        "📝 **Пиши заметки** — я извлеку важное автоматически\n\n"
        "**Примеры:**\n"
        "• «Петров по матану строгий, любит теорию»\n"
        "• «Контрольная по физике 15 февраля»",
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
        "/summary - AI-выжимка по предмету\n"
        "/upload - Загрузить данные семестра\n"
        "/settings - Настройки напоминаний\n\n"
        "**Загрузка семестра:**\n"
        "Отправь файл (PDF, JSON, TXT) или текст с:\n"
        "• Расписанием занятий\n"
        "• Списком преподавателей\n"
        "• Датами контрольных/экзаменов\n\n"
        "**Заметки:**\n"
        "Просто пиши — я пойму и сохраню.",
        parse_mode="Markdown"
    )


@dp.message(Command("teachers"))
async def cmd_teachers(message: Message):
    """Показывает список преподавателей."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Teacher)
            .options(selectinload(Teacher.subject_teachers).selectinload(SubjectTeacher.subject))
            .where(Teacher.user_id == user.id)
        )
        teachers = result.scalars().all()

    if not teachers:
        await message.answer(
            "У тебя пока нет преподавателей.\n"
            "Напиши заметку или загрузи данные семестра!",
            reply_markup=get_main_keyboard()
        )
        return

    text = "👨‍🏫 **Преподаватели:**\n\n"
    for teacher in teachers:
        text += f"👤 **{teacher.name}**\n"
        if teacher.temperament:
            text += f"   🎭 {teacher.temperament}\n"
        if teacher.preferences:
            text += f"   💡 {teacher.preferences}\n"

        subjects = [st.subject.name for st in teacher.subject_teachers]
        if subjects:
            roles = {st.subject.name: st.role for st in teacher.subject_teachers}
            for subj in subjects:
                role_emoji = "📖" if roles[subj] == "lecturer" else "✏️"
                text += f"   {role_emoji} {subj}\n"
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
            .limit(10)
        )
        deadlines = result.scalars().all()

    if not deadlines:
        await message.answer(
            "Нет активных дедлайнов! 🎉",
            reply_markup=get_main_keyboard()
        )
        return

    text = "📅 **Ближайшие дедлайны:**\n\n"
    for d in deadlines:
        date_str = d.deadline_date.strftime("%d.%m %H:%M")
        days_left = (d.deadline_date - datetime.now()).days

        emoji = "🟢" if days_left > 7 else "🟡" if days_left > 2 else "🔴"
        status = f"({days_left} дн.)" if days_left >= 0 else "⚠️ ПРОСРОЧЕНО"

        text += f"{emoji} **{d.title}**\n"
        text += f"   📚 {d.subject.name} | {d.work_type}\n"
        text += f"   ⏰ {date_str} {status}\n"
        if d.ai_hint:
            text += f"   💡 {d.ai_hint[:60]}...\n"
        text += "\n"

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("summary"))
async def cmd_summary(message: Message):
    """Генерирует AI-выжимку по предмету."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Subject).where(Subject.user_id == user.id)
        )
        subjects = result.scalars().all()

    if not subjects:
        await message.answer("Нет предметов. Сначала добавь данные!")
        return

    # Создаём кнопки для выбора предмета
    buttons = []
    for subj in subjects[:10]:
        buttons.append([InlineKeyboardButton(
            text=subj.name,
            callback_data=f"summary_{subj.id}"
        )])

    await message.answer(
        "Выбери предмет для AI-выжимки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@dp.callback_query(F.data.startswith("summary_"))
async def callback_summary(callback: CallbackQuery):
    """Генерирует выжимку по выбранному предмету."""
    subject_id = int(callback.data.split("_")[1])
    await callback.answer("Генерирую выжимку...")

    user = await get_or_create_user(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(Subject)
            .options(selectinload(Subject.materials), selectinload(Subject.notes))
            .where(Subject.id == subject_id, Subject.user_id == user.id)
        )
        subject = result.scalar_one_or_none()

        if not subject:
            await callback.message.answer("Предмет не найден")
            return

        materials_text = "\n".join([f"{m.title}: {m.description or ''}" for m in subject.materials[:10]])
        notes_text = "\n".join([n.raw_text for n in subject.notes[:10]])

        summary = await gpt_service.generate_subject_summary(subject.name, materials_text, notes_text)

        subject.ai_summary = summary
        await session.commit()

    await callback.message.answer(
        f"📚 **{subject.name}** — AI выжимка:\n\n{summary}",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("upload"))
async def cmd_upload(message: Message, state: FSMContext):
    """Начинает процесс загрузки семестра."""
    await state.set_state(SemesterUploadStates.waiting_for_data)
    await message.answer(
        "📤 **Загрузка данных семестра**\n\n"
        "Отправь мне:\n"
        "• Файл (PDF, JSON, TXT) с расписанием\n"
        "• Или текст с информацией о предметах\n\n"
        "**Пример текста:**\n"
        "```\n"
        "Математика - Иванов И.И. (лекции), Петров П.П. (практики)\n"
        "Пн 9:00-10:30 лекция\n"
        "Контрольная 15.02\n"
        "```\n\n"
        "Отправь /cancel для отмены.",
        parse_mode="Markdown"
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отменяет текущую операцию."""
    await state.clear()
    await message.answer("Операция отменена.", reply_markup=get_main_keyboard())


@dp.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext):
    """Настройки напоминаний."""
    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(ReminderSettings).where(ReminderSettings.user_id == user.id)
        )
        rs = result.scalar_one_or_none()

    current = rs.hours_before if rs else [72, 24, 12]
    current_str = ", ".join([f"{h}ч" for h in current])

    await state.set_state(ReminderSettingsStates.waiting_for_hours)
    await message.answer(
        f"⚙️ **Настройки напоминаний**\n\n"
        f"Сейчас: {current_str}\n\n"
        "Введи через запятую за сколько часов напоминать.\n"
        "Например: `72, 24, 6`\n\n"
        "/cancel для отмены",
        parse_mode="Markdown"
    )


@dp.message(ReminderSettingsStates.waiting_for_hours)
async def process_reminder_settings(message: Message, state: FSMContext):
    """Обрабатывает настройки напоминаний."""
    if message.text.startswith("/"):
        return

    try:
        hours = [int(h.strip()) for h in message.text.split(",")]
        hours = sorted(hours, reverse=True)
    except ValueError:
        await message.answer("❌ Неверный формат. Пример: 72, 24, 12")
        return

    user = await get_or_create_user(message.from_user.id)

    async with async_session() as session:
        reminder_service = ReminderService(session)
        await reminder_service.update_user_settings(user.id, hours)

    await state.clear()
    hours_str = ", ".join([f"{h}ч" for h in hours])
    await message.answer(
        f"✅ Сохранено! Напоминания за: {hours_str}",
        reply_markup=get_main_keyboard()
    )


# Обработка файлов для загрузки семестра
@dp.message(SemesterUploadStates.waiting_for_data, F.document)
async def process_semester_file(message: Message, state: FSMContext):
    """Обрабатывает загруженный файл семестра."""
    user = await get_or_create_user(message.from_user.id)
    doc = message.document

    await message.answer("⏳ Обрабатываю файл...")

    try:
        file = await bot.get_file(doc.file_id)
        content = await bot.download_file(file.file_path)
        data = content.read()

        if doc.file_name.endswith(".pdf"):
            try:
                import fitz
                pdf_doc = fitz.open(stream=data, filetype="pdf")
                text = ""
                for page in pdf_doc:
                    text += page.get_text()
                pdf_doc.close()
            except ImportError:
                await message.answer("❌ PDF не поддерживается. Отправь TXT или JSON.")
                return
        elif doc.file_name.endswith(".json"):
            text = data.decode("utf-8")
        else:
            text = data.decode("utf-8")

        await _process_semester_text(message, state, user, text)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        await state.clear()


@dp.message(SemesterUploadStates.waiting_for_data, F.text)
async def process_semester_text_msg(message: Message, state: FSMContext):
    """Обрабатывает текст семестра."""
    if message.text.startswith("/"):
        return

    user = await get_or_create_user(message.from_user.id)
    await message.answer("⏳ Анализирую данные...")
    await _process_semester_text(message, state, user, message.text)


async def _process_semester_text(message: Message, state: FSMContext, user: User, text: str):
    """Парсит и сохраняет данные семестра."""
    await bot.send_chat_action(message.chat.id, "typing")

    parsed = await gpt_service.parse_semester_data(text)

    async with async_session() as session:
        created = {"subjects": 0, "teachers": 0, "materials": 0, "schedules": 0, "deadlines": 0}

        for subj_data in parsed.get("subjects", []):
            # Создаём предмет
            result = await session.execute(
                select(Subject).where(Subject.user_id == user.id, Subject.name == subj_data["name"])
            )
            subject = result.scalar_one_or_none()
            if not subject:
                subject = Subject(user_id=user.id, name=subj_data["name"])
                session.add(subject)
                await session.flush()
                created["subjects"] += 1

            # Создаём преподавателей
            for t_data in subj_data.get("teachers", []):
                result = await session.execute(
                    select(Teacher).where(Teacher.user_id == user.id, Teacher.name == t_data["name"])
                )
                teacher = result.scalar_one_or_none()
                if not teacher:
                    teacher = Teacher(user_id=user.id, name=t_data["name"])
                    session.add(teacher)
                    await session.flush()
                    created["teachers"] += 1

                role = t_data.get("role", "lecturer")
                result = await session.execute(
                    select(SubjectTeacher).where(
                        SubjectTeacher.subject_id == subject.id,
                        SubjectTeacher.teacher_id == teacher.id
                    )
                )
                if not result.scalar_one_or_none():
                    session.add(SubjectTeacher(subject_id=subject.id, teacher_id=teacher.id, role=role))

            # Создаём материалы
            for idx, m_data in enumerate(subj_data.get("materials", [])):
                scheduled_date = None
                if m_data.get("date"):
                    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                        try:
                            scheduled_date = datetime.strptime(m_data["date"], fmt)
                            break
                        except ValueError:
                            continue

                material = SemesterMaterial(
                    subject_id=subject.id, material_type=m_data.get("type", "other"),
                    title=m_data.get("title", f"Материал {idx + 1}"),
                    description=m_data.get("description"), scheduled_date=scheduled_date,
                    order_index=idx
                )
                session.add(material)
                created["materials"] += 1

                # Автоматически создаём дедлайны для тестов/экзаменов
                if m_data.get("type") in ("test", "exam") and scheduled_date:
                    ai_hint = await gpt_service.generate_deadline_hint(
                        f"{m_data.get('title', 'Тест')} по {subject.name}"
                    )
                    deadline = Deadline(
                        subject_id=subject.id,
                        title=m_data.get("title", "Тест"),
                        work_type="Тест" if m_data["type"] == "test" else "Экзамен",
                        description=m_data.get("description"),
                        deadline_date=scheduled_date,
                        ai_hint=ai_hint
                    )
                    session.add(deadline)
                    created["deadlines"] += 1

        # Отдельные дедлайны
        for d_data in parsed.get("deadlines", []):
            subj_name = d_data.get("subject", "Другое")
            result = await session.execute(
                select(Subject).where(Subject.user_id == user.id, Subject.name == subj_name)
            )
            subject = result.scalar_one_or_none()
            if not subject:
                subject = Subject(user_id=user.id, name=subj_name)
                session.add(subject)
                await session.flush()

            try:
                deadline_date = datetime.strptime(d_data.get("deadline_date", ""), "%Y-%m-%d %H:%M")
            except ValueError:
                continue

            ai_hint = await gpt_service.generate_deadline_hint(
                f"{d_data.get('title', 'Работа')} ({d_data.get('work_type', '')}) по {subj_name}"
            )

            deadline = Deadline(
                subject_id=subject.id, title=d_data.get("title", "Работа"),
                work_type=d_data.get("work_type", "Другое"),
                description=d_data.get("description"), deadline_date=deadline_date,
                ai_hint=ai_hint
            )
            session.add(deadline)
            created["deadlines"] += 1

        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ **Данные загружены!**\n\n"
        f"📚 Предметов: {created['subjects']}\n"
        f"👨‍🏫 Преподавателей: {created['teachers']}\n"
        f"📖 Материалов: {created['materials']}\n"
        f"📅 Дедлайнов: {created['deadlines']}\n\n"
        "Открой приложение для просмотра!",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# Callback handlers
@dp.callback_query(F.data == "teachers")
async def callback_teachers(callback: CallbackQuery):
    await callback.answer()
    # Создаём новое сообщение от имени пользователя
    callback.message.from_user = callback.from_user
    await cmd_teachers(callback.message)


@dp.callback_query(F.data == "deadlines")
async def callback_deadlines(callback: CallbackQuery):
    await callback.answer()
    callback.message.from_user = callback.from_user
    await cmd_deadlines(callback.message)


@dp.callback_query(F.data == "reminder_settings")
async def callback_reminder_settings(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    callback.message.from_user = callback.from_user
    await cmd_settings(callback.message, state)


@dp.callback_query(F.data == "upload_semester")
async def callback_upload_semester(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    callback.message.from_user = callback.from_user
    await cmd_upload(callback.message, state)


# Обработка обычных текстовых сообщений (заметки)
@dp.message(F.text)
async def process_note(message: Message, state: FSMContext):
    """Обрабатывает текстовые заметки пользователя."""
    # Пропускаем команды
    if message.text.startswith("/"):
        return

    user = await get_or_create_user(message.from_user.id)
    await bot.send_chat_action(message.chat.id, "typing")

    parsed_data = await gpt_service.parse_note(message.text)

    async with async_session() as session:
        # Определяем тип заметки
        note_type = parsed_data.get("note_type", "note")
        enhanced_desc = parsed_data.get("enhanced_description", message.text)

        # Сохраняем заметку
        note = Note(
            user_id=user.id,
            raw_text=message.text,
            parsed_data=parsed_data,
            note_type=note_type,
            is_processed=True
        )
        session.add(note)

        response_parts = []

        # Обрабатываем преподавателя
        if parsed_data.get("teacher"):
            t_data = parsed_data["teacher"]
            subj_name = t_data.get("subject", "Неизвестный предмет")

            result = await session.execute(
                select(Subject).where(Subject.user_id == user.id, Subject.name == subj_name)
            )
            subject = result.scalar_one_or_none()
            if not subject:
                subject = Subject(user_id=user.id, name=subj_name)
                session.add(subject)
                await session.flush()

            # Ищем или создаём преподавателя
            result = await session.execute(
                select(Teacher).where(Teacher.user_id == user.id, Teacher.name == t_data.get("name", ""))
            )
            teacher = result.scalar_one_or_none()

            if teacher:
                if t_data.get("temperament"):
                    teacher.temperament = t_data["temperament"]
                if t_data.get("preferences"):
                    teacher.preferences = (teacher.preferences or "") + "\n" + t_data["preferences"]
                if t_data.get("notes"):
                    teacher.notes = (teacher.notes or "") + "\n" + t_data["notes"]
            else:
                teacher = Teacher(
                    user_id=user.id,
                    name=t_data.get("name", "Неизвестно"),
                    temperament=t_data.get("temperament"),
                    preferences=t_data.get("preferences"),
                    notes=t_data.get("notes")
                )
                session.add(teacher)
                await session.flush()

            # Привязываем к предмету
            role = t_data.get("role", "lecturer")
            result = await session.execute(
                select(SubjectTeacher).where(
                    SubjectTeacher.subject_id == subject.id,
                    SubjectTeacher.teacher_id == teacher.id
                )
            )
            if not result.scalar_one_or_none():
                session.add(SubjectTeacher(subject_id=subject.id, teacher_id=teacher.id, role=role))

            note.subject_id = subject.id
            response_parts.append(f"👨‍🏫 {teacher.name} ({subj_name})")

        # Обрабатываем дедлайн
        if parsed_data.get("deadline"):
            d_data = parsed_data["deadline"]
            subj_name = d_data.get("subject", "Другое")

            result = await session.execute(
                select(Subject).where(Subject.user_id == user.id, Subject.name == subj_name)
            )
            subject = result.scalar_one_or_none()
            if not subject:
                subject = Subject(user_id=user.id, name=subj_name)
                session.add(subject)
                await session.flush()

            try:
                deadline_date = datetime.strptime(d_data.get("deadline_date", ""), "%Y-%m-%d %H:%M")
            except ValueError:
                deadline_date = datetime.now()

            ai_hint = await gpt_service.generate_deadline_hint(
                f"{d_data.get('title', 'Работа')} ({d_data.get('work_type', '')}) по {subj_name}"
            )

            deadline = Deadline(
                subject_id=subject.id,
                title=d_data.get("title", "Работа"),
                work_type=d_data.get("work_type", "Другое"),
                description=d_data.get("description"),
                deadline_date=deadline_date,
                ai_hint=ai_hint
            )
            session.add(deadline)
            await session.flush()

            reminder_service = ReminderService(session)
            await reminder_service.create_reminders_for_deadline(deadline, user.id)

            note.subject_id = subject.id
            date_str = deadline_date.strftime("%d.%m.%Y %H:%M")
            response_parts.append(f"📅 {deadline.title} — {date_str}")

        await session.commit()

        # Формируем ответ
        type_emoji = {"note": "📝", "preference": "💭", "tip": "💡", "material": "📚"}.get(note_type, "📝")

        if response_parts:
            response = f"{type_emoji} Сохранено:\n" + "\n".join(response_parts)
            if enhanced_desc != message.text:
                response += f"\n\n✨ {enhanced_desc}"
        else:
            response = f"{type_emoji} Заметка сохранена"

    await message.answer(response, reply_markup=get_main_keyboard())


async def setup_bot():
    """Настройка бота."""
    pass
