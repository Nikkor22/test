from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
import enum


class TeacherRole(str, enum.Enum):
    LECTURER = "lecturer"
    PRACTITIONER = "practitioner"


class NoteType(str, enum.Enum):
    NOTE = "note"                # общая заметка
    PREFERENCE = "preference"    # предпочтения преподавателя
    TIP = "tip"                  # совет по подготовке
    MATERIAL = "material"        # учебный материал


class MaterialType(str, enum.Enum):
    LECTURE = "lecture"
    PRACTICE = "practice"
    LAB = "lab"
    TEST = "test"
    EXAM = "exam"
    OTHER = "other"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subjects: Mapped[List["Subject"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    teachers: Mapped[List["Teacher"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notes: Mapped[List["Note"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminder_settings: Mapped[Optional["ReminderSettings"]] = relationship(back_populates="user", uselist=False)
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI выжимка по предмету
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subjects")
    subject_teachers: Mapped[List["SubjectTeacher"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    deadlines: Mapped[List["Deadline"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    materials: Mapped[List["SemesterMaterial"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    notes: Mapped[List["Note"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    temperament: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="teachers")
    subject_teachers: Mapped[List["SubjectTeacher"]] = relationship(back_populates="teacher", cascade="all, delete-orphan")


class SubjectTeacher(Base):
    """Связь преподавателя с предметом. Роль: лектор или практикант."""
    __tablename__ = "subject_teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(50))  # "lecturer" or "practitioner"

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="subject_teachers")
    teacher: Mapped["Teacher"] = relationship(back_populates="subject_teachers")


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    work_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI подсказка: что повторить
    deadline_date: Mapped[datetime] = mapped_column(DateTime)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="deadlines")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="deadline", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    note_type: Mapped[str] = mapped_column(String(50), default="note")  # note, preference, tip, material
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notes")
    subject: Mapped[Optional["Subject"]] = relationship(back_populates="notes")


class SemesterMaterial(Base):
    """Материалы семестра: лекции, практики, лабораторные, тесты."""
    __tablename__ = "semester_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    material_type: Mapped[str] = mapped_column(String(50))  # lecture, practice, lab, test, exam
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # текст лекции
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI краткая выжимка
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)  # порядковый номер
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="materials")


class Schedule(Base):
    """Расписание занятий."""
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Пн, 1=Вт, ..., 6=Вс
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))    # "10:30"
    lesson_type: Mapped[str] = mapped_column(String(50))  # lecture, practice, lab
    pair_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # номер пары
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True)  # повторяется каждую неделю
    specific_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # конкретная дата (для разовых)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="schedules")
    subject: Mapped["Subject"] = relationship(back_populates="schedules")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    deadline_id: Mapped[int] = mapped_column(ForeignKey("deadlines.id", ondelete="CASCADE"))
    hours_before: Mapped[int] = mapped_column(Integer)
    send_at: Mapped[datetime] = mapped_column(DateTime)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    deadline: Mapped["Deadline"] = relationship(back_populates="reminders")


class ReminderSettings(Base):
    __tablename__ = "reminder_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    hours_before: Mapped[list] = mapped_column(JSON, default=[72, 24, 12])
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reminder_settings")
