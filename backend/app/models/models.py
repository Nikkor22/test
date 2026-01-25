from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    subjects: Mapped[List["Subject"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notes: Mapped[List["Note"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reminder_settings: Mapped[Optional["ReminderSettings"]] = relationship(back_populates="user", uselist=False)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subjects")
    teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="subject", uselist=False)
    deadlines: Mapped[List["Deadline"]] = relationship(back_populates="subject", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    temperament: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # что любит спрашивать
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # доп заметки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subject: Mapped["Subject"] = relationship(back_populates="teacher")


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))  # название работы
    work_type: Mapped[str] = mapped_column(String(100))  # контрольная, презентация, лабораторная и т.д.
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    raw_text: Mapped[str] = mapped_column(Text)  # оригинальный текст от пользователя
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # распарсенные данные от GPT
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notes")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    deadline_id: Mapped[int] = mapped_column(ForeignKey("deadlines.id", ondelete="CASCADE"))
    hours_before: Mapped[int] = mapped_column(Integer)  # за сколько часов до дедлайна
    send_at: Mapped[datetime] = mapped_column(DateTime)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # сгенерированное сообщение
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    deadline: Mapped["Deadline"] = relationship(back_populates="reminders")


class ReminderSettings(Base):
    __tablename__ = "reminder_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    # Список часов до дедлайна для напоминаний (по умолчанию: 72, 24, 12)
    hours_before: Mapped[list] = mapped_column(JSON, default=[72, 24, 12])
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="reminder_settings")
