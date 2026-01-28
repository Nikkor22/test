from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_session
from app.models import (
    User, Subject, Teacher, SubjectTeacher, Deadline, Note,
    SemesterMaterial, Schedule, ReminderSettings
)
from app.services.reminder_service import ReminderService
from app.services.gpt_service import GPTService

router = APIRouter(prefix="/api", tags=["api"])
gpt_service = GPTService()


# ── Pydantic models ──────────────────────────────────────────

class TeacherResponse(BaseModel):
    id: int
    name: str
    temperament: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None
    contact_info: Optional[str] = None
    subjects: List[dict] = []

    class Config:
        from_attributes = True


class TeacherCreate(BaseModel):
    name: str
    temperament: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None
    contact_info: Optional[str] = None


class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    temperament: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None
    contact_info: Optional[str] = None


class SubjectTeacherLink(BaseModel):
    teacher_id: int
    role: str


class SubjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    ai_summary: Optional[str] = None
    teachers: List[dict] = []

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DeadlineResponse(BaseModel):
    id: int
    title: str
    work_type: str
    description: Optional[str] = None
    ai_hint: Optional[str] = None
    deadline_date: datetime
    is_completed: bool
    subject_name: str
    subject_id: int

    class Config:
        from_attributes = True


class DeadlineCreate(BaseModel):
    subject_id: int
    title: str
    work_type: str
    description: Optional[str] = None
    deadline_date: datetime


class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    work_type: Optional[str] = None
    description: Optional[str] = None
    deadline_date: Optional[datetime] = None
    is_completed: Optional[bool] = None


class NoteResponse(BaseModel):
    id: int
    note_type: str
    raw_text: str
    parsed_data: Optional[dict] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MaterialResponse(BaseModel):
    id: int
    subject_id: int
    material_type: str
    title: str
    description: Optional[str] = None
    ai_summary: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    order_index: int = 0

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    subject_id: int
    material_type: str
    title: str
    description: Optional[str] = None
    content_text: Optional[str] = None
    scheduled_date: Optional[datetime] = None


class ScheduleResponse(BaseModel):
    id: int
    subject_id: int
    subject_name: str
    day_of_week: int
    start_time: str
    end_time: str
    lesson_type: str
    pair_number: Optional[int] = None
    teacher_name: Optional[str] = None

    class Config:
        from_attributes = True


class ScheduleCreate(BaseModel):
    subject_id: int
    day_of_week: int
    start_time: str
    end_time: str
    lesson_type: str
    pair_number: Optional[int] = None


class ReminderSettingsResponse(BaseModel):
    hours_before: List[int]
    is_enabled: bool

    class Config:
        from_attributes = True


class ReminderSettingsUpdate(BaseModel):
    hours_before: Optional[List[int]] = None
    is_enabled: Optional[bool] = None


class SemesterUpload(BaseModel):
    text: str


# ── Helpers ──────────────────────────────────────────────────

async def get_user_by_telegram_id(telegram_id: int, session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ── Teachers ─────────────────────────────────────────────────

@router.get("/teachers", response_model=List[TeacherResponse])
async def get_teachers(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Teacher)
        .options(selectinload(Teacher.subject_teachers).selectinload(SubjectTeacher.subject))
        .where(Teacher.user_id == user.id)
    )
    teachers = result.scalars().all()

    return [
        TeacherResponse(
            id=t.id, name=t.name, temperament=t.temperament,
            preferences=t.preferences, notes=t.notes, contact_info=t.contact_info,
            subjects=[
                {"subject_id": st.subject_id, "subject_name": st.subject.name, "role": st.role}
                for st in t.subject_teachers
            ]
        )
        for t in teachers
    ]


@router.post("/teachers", response_model=TeacherResponse)
async def create_teacher(
    data: TeacherCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    teacher = Teacher(user_id=user.id, **data.model_dump())
    session.add(teacher)
    await session.commit()
    await session.refresh(teacher)
    return TeacherResponse(id=teacher.id, name=teacher.name, temperament=teacher.temperament,
                           preferences=teacher.preferences, notes=teacher.notes,
                           contact_info=teacher.contact_info, subjects=[])


@router.put("/teachers/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Teacher)
        .options(selectinload(Teacher.subject_teachers).selectinload(SubjectTeacher.subject))
        .where(Teacher.id == teacher_id, Teacher.user_id == user.id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(teacher, key, value)
    await session.commit()
    await session.refresh(teacher)

    return TeacherResponse(
        id=teacher.id, name=teacher.name, temperament=teacher.temperament,
        preferences=teacher.preferences, notes=teacher.notes, contact_info=teacher.contact_info,
        subjects=[
            {"subject_id": st.subject_id, "subject_name": st.subject.name, "role": st.role}
            for st in teacher.subject_teachers
        ]
    )


@router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Teacher).where(Teacher.id == teacher_id, Teacher.user_id == user.id)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    await session.delete(teacher)
    await session.commit()
    return {"status": "ok"}


# ── Subjects ─────────────────────────────────────────────────

@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject)
        .options(selectinload(Subject.subject_teachers).selectinload(SubjectTeacher.teacher))
        .where(Subject.user_id == user.id)
    )
    subjects = result.scalars().all()

    return [
        SubjectResponse(
            id=s.id, name=s.name, description=s.description, ai_summary=s.ai_summary,
            teachers=[
                {"teacher_id": st.teacher_id, "teacher_name": st.teacher.name, "role": st.role}
                for st in s.subject_teachers
            ]
        )
        for s in subjects
    ]


@router.post("/subjects", response_model=SubjectResponse)
async def create_subject(
    data: SubjectCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    subject = Subject(user_id=user.id, name=data.name, description=data.description)
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return SubjectResponse(id=subject.id, name=subject.name, description=subject.description, teachers=[])


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await session.delete(subject)
    await session.commit()
    return {"status": "ok"}


@router.post("/subjects/{subject_id}/link-teacher")
async def link_teacher_to_subject(
    subject_id: int,
    data: SubjectTeacherLink,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject).where(Subject.id == subject_id, Subject.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    result = await session.execute(
        select(Teacher).where(Teacher.id == data.teacher_id, Teacher.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Teacher not found")

    result = await session.execute(
        select(SubjectTeacher).where(
            SubjectTeacher.subject_id == subject_id,
            SubjectTeacher.teacher_id == data.teacher_id,
            SubjectTeacher.role == data.role
        )
    )
    if result.scalar_one_or_none():
        return {"status": "already_linked"}

    link = SubjectTeacher(subject_id=subject_id, teacher_id=data.teacher_id, role=data.role)
    session.add(link)
    await session.commit()
    return {"status": "ok"}


@router.delete("/subjects/{subject_id}/unlink-teacher/{teacher_id}")
async def unlink_teacher(
    subject_id: int,
    teacher_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(SubjectTeacher).join(Subject)
        .where(SubjectTeacher.subject_id == subject_id,
               SubjectTeacher.teacher_id == teacher_id,
               Subject.user_id == user.id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await session.delete(link)
    await session.commit()
    return {"status": "ok"}


@router.post("/subjects/{subject_id}/summary")
async def generate_subject_summary(
    subject_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject)
        .options(selectinload(Subject.materials), selectinload(Subject.notes))
        .where(Subject.id == subject_id, Subject.user_id == user.id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    materials_text = "\n".join([f"{m.title}: {m.description or ''}" for m in subject.materials])
    notes_text = "\n".join([n.raw_text for n in subject.notes[:10]])

    summary = await gpt_service.generate_subject_summary(subject.name, materials_text, notes_text)
    subject.ai_summary = summary
    await session.commit()
    return {"summary": summary}


# ── Deadlines ────────────────────────────────────────────────

@router.get("/deadlines", response_model=List[DeadlineResponse])
async def get_deadlines(
    telegram_id: int = Query(...),
    show_completed: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    query = (
        select(Deadline).join(Subject)
        .options(selectinload(Deadline.subject))
        .where(Subject.user_id == user.id)
        .order_by(Deadline.deadline_date)
    )
    if not show_completed:
        query = query.where(Deadline.is_completed == False)

    result = await session.execute(query)
    deadlines = result.scalars().all()

    return [
        DeadlineResponse(
            id=d.id, title=d.title, work_type=d.work_type, description=d.description,
            ai_hint=d.ai_hint, deadline_date=d.deadline_date, is_completed=d.is_completed,
            subject_name=d.subject.name, subject_id=d.subject_id
        )
        for d in deadlines
    ]


@router.post("/deadlines", response_model=DeadlineResponse)
async def create_deadline(
    data: DeadlineCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject).where(Subject.id == data.subject_id, Subject.user_id == user.id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    hint_info = f"{data.title} ({data.work_type}) по {subject.name}"
    if data.description:
        hint_info += f": {data.description}"
    ai_hint = await gpt_service.generate_deadline_hint(hint_info)

    deadline = Deadline(
        subject_id=data.subject_id, title=data.title, work_type=data.work_type,
        description=data.description, deadline_date=data.deadline_date, ai_hint=ai_hint
    )
    session.add(deadline)
    await session.flush()

    reminder_service = ReminderService(session)
    await reminder_service.create_reminders_for_deadline(deadline, user.id)
    await session.commit()
    await session.refresh(deadline)

    return DeadlineResponse(
        id=deadline.id, title=deadline.title, work_type=deadline.work_type,
        description=deadline.description, ai_hint=deadline.ai_hint,
        deadline_date=deadline.deadline_date, is_completed=deadline.is_completed,
        subject_name=subject.name, subject_id=deadline.subject_id
    )


@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: int,
    data: DeadlineUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Deadline).join(Subject)
        .options(selectinload(Deadline.subject))
        .where(Deadline.id == deadline_id, Subject.user_id == user.id)
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(deadline, key, value)
    await session.commit()
    await session.refresh(deadline)

    return DeadlineResponse(
        id=deadline.id, title=deadline.title, work_type=deadline.work_type,
        description=deadline.description, ai_hint=deadline.ai_hint,
        deadline_date=deadline.deadline_date, is_completed=deadline.is_completed,
        subject_name=deadline.subject.name, subject_id=deadline.subject_id
    )


@router.delete("/deadlines/{deadline_id}")
async def delete_deadline(
    deadline_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Deadline).join(Subject)
        .where(Deadline.id == deadline_id, Subject.user_id == user.id)
    )
    deadline = result.scalar_one_or_none()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    await session.delete(deadline)
    await session.commit()
    return {"status": "ok"}


# ── Notes ────────────────────────────────────────────────────

@router.get("/notes", response_model=List[NoteResponse])
async def get_notes(
    telegram_id: int = Query(...),
    note_type: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    query = (
        select(Note).options(selectinload(Note.subject))
        .where(Note.user_id == user.id)
        .order_by(Note.created_at.desc())
    )
    if note_type:
        query = query.where(Note.note_type == note_type)
    if subject_id:
        query = query.where(Note.subject_id == subject_id)

    result = await session.execute(query)
    notes = result.scalars().all()

    return [
        NoteResponse(
            id=n.id, note_type=n.note_type, raw_text=n.raw_text,
            parsed_data=n.parsed_data, subject_id=n.subject_id,
            subject_name=n.subject.name if n.subject else None,
            created_at=n.created_at
        )
        for n in notes
    ]


# ── Materials ────────────────────────────────────────────────

@router.get("/materials", response_model=List[MaterialResponse])
async def get_materials(
    telegram_id: int = Query(...),
    subject_id: Optional[int] = Query(None),
    material_type: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    query = (
        select(SemesterMaterial).join(Subject)
        .where(Subject.user_id == user.id)
        .order_by(SemesterMaterial.order_index)
    )
    if subject_id:
        query = query.where(SemesterMaterial.subject_id == subject_id)
    if material_type:
        query = query.where(SemesterMaterial.material_type == material_type)

    result = await session.execute(query)
    materials = result.scalars().all()

    return [
        MaterialResponse(
            id=m.id, subject_id=m.subject_id, material_type=m.material_type,
            title=m.title, description=m.description, ai_summary=m.ai_summary,
            scheduled_date=m.scheduled_date, order_index=m.order_index
        )
        for m in materials
    ]


@router.post("/materials", response_model=MaterialResponse)
async def create_material(
    data: MaterialCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject).where(Subject.id == data.subject_id, Subject.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subject not found")

    ai_summary = None
    if data.content_text:
        ai_summary = await gpt_service.summarize_material(data.title, data.content_text)

    material = SemesterMaterial(
        subject_id=data.subject_id, material_type=data.material_type,
        title=data.title, description=data.description,
        content_text=data.content_text, ai_summary=ai_summary,
        scheduled_date=data.scheduled_date
    )
    session.add(material)
    await session.commit()
    await session.refresh(material)

    return MaterialResponse(
        id=material.id, subject_id=material.subject_id, material_type=material.material_type,
        title=material.title, description=material.description, ai_summary=material.ai_summary,
        scheduled_date=material.scheduled_date, order_index=material.order_index
    )


@router.delete("/materials/{material_id}")
async def delete_material(
    material_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(SemesterMaterial).join(Subject)
        .where(SemesterMaterial.id == material_id, Subject.user_id == user.id)
    )
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    await session.delete(material)
    await session.commit()
    return {"status": "ok"}


# ── Schedule ─────────────────────────────────────────────────

@router.get("/schedule", response_model=List[ScheduleResponse])
async def get_schedule(
    telegram_id: int = Query(...),
    day_of_week: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    query = (
        select(Schedule)
        .options(selectinload(Schedule.subject).selectinload(Subject.subject_teachers).selectinload(SubjectTeacher.teacher))
        .where(Schedule.user_id == user.id)
        .order_by(Schedule.day_of_week, Schedule.start_time)
    )
    if day_of_week is not None:
        query = query.where(Schedule.day_of_week == day_of_week)

    result = await session.execute(query)
    schedules = result.scalars().all()

    response = []
    for s in schedules:
        teacher_name = None
        for st in s.subject.subject_teachers:
            if s.lesson_type == "lecture" and st.role == "lecturer":
                teacher_name = st.teacher.name
                break
            elif s.lesson_type in ("practice", "lab") and st.role == "practitioner":
                teacher_name = st.teacher.name
                break
        if not teacher_name and s.subject.subject_teachers:
            teacher_name = s.subject.subject_teachers[0].teacher.name

        response.append(ScheduleResponse(
            id=s.id, subject_id=s.subject_id, subject_name=s.subject.name,
            day_of_week=s.day_of_week, start_time=s.start_time, end_time=s.end_time,
            lesson_type=s.lesson_type, pair_number=s.pair_number, teacher_name=teacher_name
        ))
    return response


@router.post("/schedule", response_model=ScheduleResponse)
async def create_schedule(
    data: ScheduleCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Subject).where(Subject.id == data.subject_id, Subject.user_id == user.id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    schedule = Schedule(
        user_id=user.id, subject_id=data.subject_id,
        day_of_week=data.day_of_week, start_time=data.start_time,
        end_time=data.end_time, lesson_type=data.lesson_type,
        pair_number=data.pair_number
    )
    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    return ScheduleResponse(
        id=schedule.id, subject_id=schedule.subject_id, subject_name=subject.name,
        day_of_week=schedule.day_of_week, start_time=schedule.start_time,
        end_time=schedule.end_time, lesson_type=schedule.lesson_type,
        pair_number=schedule.pair_number
    )


@router.delete("/schedule/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user.id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await session.delete(schedule)
    await session.commit()
    return {"status": "ok"}


# ── Semester Upload ──────────────────────────────────────────

@router.post("/semester/upload-text")
async def upload_semester_text(
    data: SemesterUpload,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    parsed = await gpt_service.parse_semester_data(data.text)
    return await _process_semester_data(parsed, user, session)


@router.post("/semester/upload-json")
async def upload_semester_json(
    telegram_id: int = Query(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    import json
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    if "subjects" in data:
        return await _process_semester_data(data, user, session)

    parsed = await gpt_service.parse_semester_data(json.dumps(data, ensure_ascii=False))
    return await _process_semester_data(parsed, user, session)


@router.post("/semester/upload-file")
async def upload_semester_file(
    telegram_id: int = Query(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    content = await file.read()

    if file.filename and file.filename.endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
        except ImportError:
            raise HTTPException(status_code=500, detail="PDF support requires PyMuPDF")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

    parsed = await gpt_service.parse_semester_data(text)
    return await _process_semester_data(parsed, user, session)


async def _process_semester_data(parsed: dict, user: User, session: AsyncSession) -> dict:
    created = {"subjects": 0, "teachers": 0, "materials": 0, "schedules": 0, "deadlines": 0}

    for subj_data in parsed.get("subjects", []):
        result = await session.execute(
            select(Subject).where(Subject.user_id == user.id, Subject.name == subj_data["name"])
        )
        subject = result.scalar_one_or_none()
        if not subject:
            subject = Subject(user_id=user.id, name=subj_data["name"])
            session.add(subject)
            await session.flush()
            created["subjects"] += 1

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
                    SubjectTeacher.teacher_id == teacher.id,
                    SubjectTeacher.role == role
                )
            )
            if not result.scalar_one_or_none():
                session.add(SubjectTeacher(subject_id=subject.id, teacher_id=teacher.id, role=role))

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

            if m_data.get("type") in ("test", "exam") and scheduled_date:
                deadline = Deadline(
                    subject_id=subject.id,
                    title=m_data.get("title", "Тест"),
                    work_type="Тест" if m_data["type"] == "test" else "Экзамен",
                    description=m_data.get("description"),
                    deadline_date=scheduled_date
                )
                session.add(deadline)
                created["deadlines"] += 1

        for s_data in subj_data.get("schedule", []):
            schedule = Schedule(
                user_id=user.id, subject_id=subject.id,
                day_of_week=s_data.get("day_of_week", 0),
                start_time=s_data.get("start_time", "09:00"),
                end_time=s_data.get("end_time", "10:30"),
                lesson_type=s_data.get("lesson_type", "lecture"),
                pair_number=s_data.get("pair_number")
            )
            session.add(schedule)
            created["schedules"] += 1

    for d_data in parsed.get("deadlines", []):
        subj_name = d_data.get("subject", "")
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

        deadline = Deadline(
            subject_id=subject.id, title=d_data.get("title", "Работа"),
            work_type=d_data.get("work_type", "Другое"),
            description=d_data.get("description"), deadline_date=deadline_date
        )
        session.add(deadline)
        created["deadlines"] += 1

    await session.commit()
    return {"status": "ok", "created": created}


# ── Reminder Settings ────────────────────────────────────────

@router.get("/settings/reminders", response_model=ReminderSettingsResponse)
async def get_reminder_settings(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(ReminderSettings).where(ReminderSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return ReminderSettingsResponse(hours_before=[72, 24, 12], is_enabled=True)
    return ReminderSettingsResponse(hours_before=settings.hours_before, is_enabled=settings.is_enabled)


@router.put("/settings/reminders", response_model=ReminderSettingsResponse)
async def update_reminder_settings(
    data: ReminderSettingsUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_telegram_id(telegram_id, session)
    result = await session.execute(
        select(ReminderSettings).where(ReminderSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = ReminderSettings(
            user_id=user.id,
            hours_before=data.hours_before or [72, 24, 12],
            is_enabled=data.is_enabled if data.is_enabled is not None else True
        )
        session.add(settings)
    else:
        if data.hours_before is not None:
            settings.hours_before = data.hours_before
        if data.is_enabled is not None:
            settings.is_enabled = data.is_enabled

    await session.commit()
    await session.refresh(settings)
    return ReminderSettingsResponse(hours_before=settings.hours_before, is_enabled=settings.is_enabled)
