from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import get_session
from app.models import User, Subject, Teacher, Deadline, Note, ReminderSettings
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/api", tags=["api"])


# Pydantic models
class TeacherResponse(BaseModel):
    id: int
    name: str
    temperament: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None
    subject_name: str
    subject_id: int

    class Config:
        from_attributes = True


class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    temperament: Optional[str] = None
    preferences: Optional[str] = None
    notes: Optional[str] = None


class DeadlineResponse(BaseModel):
    id: int
    title: str
    work_type: str
    description: Optional[str] = None
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


class SubjectResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    name: str


class ReminderSettingsResponse(BaseModel):
    hours_before: List[int]
    is_enabled: bool

    class Config:
        from_attributes = True


class ReminderSettingsUpdate(BaseModel):
    hours_before: Optional[List[int]] = None
    is_enabled: Optional[bool] = None


# Helper function to get user by telegram_id
async def get_user_by_telegram_id(telegram_id: int, session: AsyncSession) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Teachers endpoints
@router.get("/teachers", response_model=List[TeacherResponse])
async def get_teachers(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Получить всех преподавателей пользователя."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Teacher)
        .join(Subject)
        .options(selectinload(Teacher.subject))
        .where(Subject.user_id == user.id)
    )
    teachers = result.scalars().all()

    return [
        TeacherResponse(
            id=t.id,
            name=t.name,
            temperament=t.temperament,
            preferences=t.preferences,
            notes=t.notes,
            subject_name=t.subject.name,
            subject_id=t.subject_id
        )
        for t in teachers
    ]


@router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Получить преподавателя по ID."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Teacher)
        .join(Subject)
        .options(selectinload(Teacher.subject))
        .where(Teacher.id == teacher_id)
        .where(Subject.user_id == user.id)
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    return TeacherResponse(
        id=teacher.id,
        name=teacher.name,
        temperament=teacher.temperament,
        preferences=teacher.preferences,
        notes=teacher.notes,
        subject_name=teacher.subject.name,
        subject_id=teacher.subject_id
    )


@router.put("/teachers/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Обновить преподавателя."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Teacher)
        .join(Subject)
        .options(selectinload(Teacher.subject))
        .where(Teacher.id == teacher_id)
        .where(Subject.user_id == user.id)
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(teacher, key, value)

    await session.commit()
    await session.refresh(teacher)

    return TeacherResponse(
        id=teacher.id,
        name=teacher.name,
        temperament=teacher.temperament,
        preferences=teacher.preferences,
        notes=teacher.notes,
        subject_name=teacher.subject.name,
        subject_id=teacher.subject_id
    )


@router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Удалить преподавателя."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Teacher)
        .join(Subject)
        .where(Teacher.id == teacher_id)
        .where(Subject.user_id == user.id)
    )
    teacher = result.scalar_one_or_none()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    await session.delete(teacher)
    await session.commit()

    return {"status": "ok"}


# Deadlines endpoints
@router.get("/deadlines", response_model=List[DeadlineResponse])
async def get_deadlines(
    telegram_id: int = Query(...),
    show_completed: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    """Получить все дедлайны пользователя."""
    user = await get_user_by_telegram_id(telegram_id, session)

    query = (
        select(Deadline)
        .join(Subject)
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
            id=d.id,
            title=d.title,
            work_type=d.work_type,
            description=d.description,
            deadline_date=d.deadline_date,
            is_completed=d.is_completed,
            subject_name=d.subject.name,
            subject_id=d.subject_id
        )
        for d in deadlines
    ]


@router.post("/deadlines", response_model=DeadlineResponse)
async def create_deadline(
    data: DeadlineCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Создать новый дедлайн."""
    user = await get_user_by_telegram_id(telegram_id, session)

    # Проверяем, что предмет принадлежит пользователю
    result = await session.execute(
        select(Subject).where(
            Subject.id == data.subject_id,
            Subject.user_id == user.id
        )
    )
    subject = result.scalar_one_or_none()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    deadline = Deadline(
        subject_id=data.subject_id,
        title=data.title,
        work_type=data.work_type,
        description=data.description,
        deadline_date=data.deadline_date
    )
    session.add(deadline)
    await session.flush()

    # Создаем напоминания
    reminder_service = ReminderService(session)
    await reminder_service.create_reminders_for_deadline(deadline, user.id)

    await session.commit()
    await session.refresh(deadline)

    return DeadlineResponse(
        id=deadline.id,
        title=deadline.title,
        work_type=deadline.work_type,
        description=deadline.description,
        deadline_date=deadline.deadline_date,
        is_completed=deadline.is_completed,
        subject_name=subject.name,
        subject_id=deadline.subject_id
    )


@router.put("/deadlines/{deadline_id}", response_model=DeadlineResponse)
async def update_deadline(
    deadline_id: int,
    data: DeadlineUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Обновить дедлайн."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Deadline)
        .join(Subject)
        .options(selectinload(Deadline.subject))
        .where(Deadline.id == deadline_id)
        .where(Subject.user_id == user.id)
    )
    deadline = result.scalar_one_or_none()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(deadline, key, value)

    await session.commit()
    await session.refresh(deadline)

    return DeadlineResponse(
        id=deadline.id,
        title=deadline.title,
        work_type=deadline.work_type,
        description=deadline.description,
        deadline_date=deadline.deadline_date,
        is_completed=deadline.is_completed,
        subject_name=deadline.subject.name,
        subject_id=deadline.subject_id
    )


@router.delete("/deadlines/{deadline_id}")
async def delete_deadline(
    deadline_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Удалить дедлайн."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Deadline)
        .join(Subject)
        .where(Deadline.id == deadline_id)
        .where(Subject.user_id == user.id)
    )
    deadline = result.scalar_one_or_none()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    await session.delete(deadline)
    await session.commit()

    return {"status": "ok"}


# Subjects endpoints
@router.get("/subjects", response_model=List[SubjectResponse])
async def get_subjects(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Получить все предметы пользователя."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Subject).where(Subject.user_id == user.id)
    )
    subjects = result.scalars().all()

    return [SubjectResponse(id=s.id, name=s.name) for s in subjects]


@router.post("/subjects", response_model=SubjectResponse)
async def create_subject(
    data: SubjectCreate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Создать новый предмет."""
    user = await get_user_by_telegram_id(telegram_id, session)

    subject = Subject(user_id=user.id, name=data.name)
    session.add(subject)
    await session.commit()
    await session.refresh(subject)

    return SubjectResponse(id=subject.id, name=subject.name)


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Удалить предмет."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(Subject).where(
            Subject.id == subject_id,
            Subject.user_id == user.id
        )
    )
    subject = result.scalar_one_or_none()

    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    await session.delete(subject)
    await session.commit()

    return {"status": "ok"}


# Reminder settings endpoints
@router.get("/settings/reminders", response_model=ReminderSettingsResponse)
async def get_reminder_settings(
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Получить настройки напоминаний."""
    user = await get_user_by_telegram_id(telegram_id, session)

    result = await session.execute(
        select(ReminderSettings).where(ReminderSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        return ReminderSettingsResponse(hours_before=[72, 24, 12], is_enabled=True)

    return ReminderSettingsResponse(
        hours_before=settings.hours_before,
        is_enabled=settings.is_enabled
    )


@router.put("/settings/reminders", response_model=ReminderSettingsResponse)
async def update_reminder_settings(
    data: ReminderSettingsUpdate,
    telegram_id: int = Query(...),
    session: AsyncSession = Depends(get_session)
):
    """Обновить настройки напоминаний."""
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

    return ReminderSettingsResponse(
        hours_before=settings.hours_before,
        is_enabled=settings.is_enabled
    )
