from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    group_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subjects: Mapped[List["Subject"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notes: Mapped[List["Note"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminder_settings: Mapped[Optional["ReminderSettings"]] = relationship(back_populates="user", uselist=False)
    title_templates: Mapped[List["TitleTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    work_settings: Mapped[Optional["UserWorkSettings"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subjects")
    teachers: Mapped[List["Teacher"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    deadlines: Mapped[List["Deadline"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    schedule_entries: Mapped[List["ScheduleEntry"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    materials: Mapped[List["Material"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    summary: Mapped[Optional["SubjectSummary"]] = relationship(back_populates="subject", uselist=False, cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="lecturer")  # lecturer / practitioner
    temperament: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    peculiarities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="teachers")


class ScheduleEntry(Base):
    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0=Monday ... 6=Sunday
    start_time: Mapped[str] = mapped_column(String(5))  # "09:00"
    end_time: Mapped[str] = mapped_column(String(5))  # "10:30"
    room: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    class_type: Mapped[str] = mapped_column(String(50), default="lecture")  # lecture/practice/lab
    week_type: Mapped[str] = mapped_column(String(10), default="both")  # both/even/odd
    teacher_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="schedule_entries")


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    work_type: Mapped[str] = mapped_column(String(100))  # homework, lab, practical, exam, coursework
    work_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # e.g., Lab #1, Lab #2
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gpt_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deadline_date: Mapped[datetime] = mapped_column(DateTime)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="deadlines")
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="deadline", cascade="all, delete-orphan")
    generated_work: Mapped[Optional["GeneratedWork"]] = relationship(back_populates="deadline", uselist=False, cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notes")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(50))  # pdf, xlsx, txt, docx
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="materials")


class SubjectSummary(Base):
    __tablename__ = "subject_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), unique=True)
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="summary")


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


class TitleTemplate(Base):
    """Шаблон титульного листа, загружаемый пользователем.
    Поддерживает плейсхолдеры: {{subject_name}}, {{date}}, {{work_type}}, {{work_number}}, {{student_name}}, {{group_number}}
    """
    __tablename__ = "title_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))  # Display name for the template
    file_name: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(1000))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # Default template for user
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="title_templates")


class GeneratedWork(Base):
    """Сгенерированная работа (лабораторная, практическая и т.д.)"""
    __tablename__ = "generated_works"

    id: Mapped[int] = mapped_column(primary_key=True)
    deadline_id: Mapped[int] = mapped_column(ForeignKey("deadlines.id", ondelete="CASCADE"), unique=True)
    title_template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("title_templates.id", ondelete="SET NULL"), nullable=True)

    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), default="docx")  # pdf, docx

    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AI-generated content

    # Status: pending -> generating -> ready -> confirmed -> sent
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # Scheduling
    scheduled_send_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # User-defined send time
    auto_send: Mapped[bool] = mapped_column(Boolean, default=False)  # Send automatically or wait for confirmation

    # Tracking
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # User confirmed sending
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    deadline: Mapped["Deadline"] = relationship(back_populates="generated_work")
    title_template: Mapped[Optional["TitleTemplate"]] = relationship()


class UserWorkSettings(Base):
    """Настройки пользователя для автоматической генерации работ"""
    __tablename__ = "user_work_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Reminder settings (in days before deadline)
    reminder_days_before: Mapped[list] = mapped_column(JSON, default=[3, 1])  # Notify 3 days and 1 day before

    # Auto-generation settings
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=True)  # Auto-generate works before deadline
    generate_days_before: Mapped[int] = mapped_column(Integer, default=5)  # Generate 5 days before deadline

    # Sending settings
    require_confirmation: Mapped[bool] = mapped_column(Boolean, default=True)  # Require user confirmation before sending
    default_send_days_before: Mapped[int] = mapped_column(Integer, default=1)  # Default: send 1 day before deadline

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="work_settings")
