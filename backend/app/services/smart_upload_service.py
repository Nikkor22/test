"""
Smart Upload Service
Automatically detects subject, work type, and deadline from filenames.
"""
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Subject, Deadline, Material
from app.config import get_settings


settings = get_settings()
MATERIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "materials")


class SmartUploadService:
    """Service for smart file uploads with auto-detection."""

    # Subject keywords for detection
    SUBJECT_PATTERNS = {
        'матан': 'Математический анализ',
        'математический анализ': 'Математический анализ',
        'линал': 'Линейная алгебра',
        'линейная алгебра': 'Линейная алгебра',
        'физик': 'Физика',
        'програм': 'Программирование',
        'информатик': 'Информатика',
        'экономик': 'Экономика',
        'философ': 'Философия',
        'истори': 'История',
        'английск': 'Английский язык',
        'базы данных': 'Базы данных',
        'бд': 'Базы данных',
        'ооп': 'ООП',
        'веб': 'Веб-разработка',
        'сети': 'Компьютерные сети',
        'моделирован': 'Моделирование',
        'бизнес': 'Бизнес-процессы',
    }

    # Work type patterns
    WORK_TYPE_PATTERNS = [
        (r'лаб(?:оратор)?\.?\s*(?:работа\s*)?[№#]?\s*(\d+)', 'lab'),
        (r'лр\s*[№#]?\s*(\d+)', 'lab'),
        (r'практ(?:ическ)?\.?\s*(?:работа\s*)?[№#]?\s*(\d+)', 'practical'),
        (r'пр\s*[№#]?\s*(\d+)', 'practical'),
        (r'дз\s*[№#]?\s*(\d+)', 'homework'),
        (r'домашн\.?\s*(?:работа\s*)?[№#]?\s*(\d+)', 'homework'),
        (r'контрольн\.?\s*(?:работа\s*)?[№#]?\s*(\d+)', 'test'),
        (r'кр\s*[№#]?\s*(\d+)', 'test'),
        (r'курсов\.?\s*(?:работа|проект)?', 'coursework'),
        (r'реферат', 'report'),
        (r'презентац', 'presentation'),
        (r'лекци[яи]?\s*[№#]?\s*(\d+)?', 'lecture'),
        (r'лк\s*[№#]?\s*(\d+)?', 'lecture'),
    ]

    # Date patterns in filenames
    DATE_PATTERNS = [
        r'(\d{2})\.(\d{2})\.(\d{4})',  # 15.03.2024
        r'(\d{2})\.(\d{2})\.(\d{2})',  # 15.03.24
        r'(\d{4})-(\d{2})-(\d{2})',    # 2024-03-15
        r'(\d{2})-(\d{2})-(\d{4})',    # 15-03-2024
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        os.makedirs(MATERIALS_DIR, exist_ok=True)

    def analyze_filename(self, filename: str) -> dict:
        """
        Analyze filename and extract metadata.
        Returns detected subject, work type, work number, and deadline.
        """
        name_lower = filename.lower()
        base_name = os.path.splitext(filename)[0]
        base_lower = base_name.lower()

        result = {
            "original_filename": filename,
            "detected_subject": None,
            "detected_work_type": None,
            "detected_work_number": None,
            "detected_deadline": None,
            "suggested_title": base_name,
            "confidence": 0.0,
        }

        # Detect subject
        for pattern, subject_name in self.SUBJECT_PATTERNS.items():
            if pattern in base_lower:
                result["detected_subject"] = subject_name
                result["confidence"] += 0.3
                break

        # Detect work type and number
        for pattern, work_type in self.WORK_TYPE_PATTERNS:
            match = re.search(pattern, base_lower)
            if match:
                result["detected_work_type"] = work_type
                result["confidence"] += 0.3
                # Extract number if present
                groups = match.groups()
                if groups and groups[0]:
                    try:
                        result["detected_work_number"] = int(groups[0])
                        result["confidence"] += 0.1
                    except ValueError:
                        pass
                break

        # Detect date
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, base_name)
            if match:
                try:
                    groups = match.groups()
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    elif len(groups[2]) == 4:  # DD.MM.YYYY or DD-MM-YYYY
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # DD.MM.YY
                        day, month, year = int(groups[0]), int(groups[1]), 2000 + int(groups[2])

                    result["detected_deadline"] = datetime(year, month, day).isoformat()
                    result["confidence"] += 0.2
                except (ValueError, IndexError):
                    pass
                break

        # Generate suggested title
        if result["detected_work_type"] and result["detected_work_number"]:
            work_labels = {
                'lab': 'Лабораторная работа',
                'practical': 'Практическая работа',
                'homework': 'Домашнее задание',
                'test': 'Контрольная работа',
                'coursework': 'Курсовая работа',
                'report': 'Реферат',
                'presentation': 'Презентация',
                'lecture': 'Лекция',
            }
            label = work_labels.get(result["detected_work_type"], result["detected_work_type"])
            result["suggested_title"] = f"{label} №{result['detected_work_number']}"
        elif result["detected_work_type"]:
            work_labels = {
                'lab': 'Лабораторная работа',
                'practical': 'Практическая работа',
                'homework': 'Домашнее задание',
                'test': 'Контрольная работа',
                'coursework': 'Курсовая работа',
                'report': 'Реферат',
                'presentation': 'Презентация',
                'lecture': 'Лекция',
            }
            result["suggested_title"] = work_labels.get(result["detected_work_type"], base_name)

        # Normalize confidence
        result["confidence"] = min(result["confidence"], 1.0)

        return result

    def analyze_multiple(self, filenames: List[str]) -> dict:
        """
        Analyze multiple filenames and find common patterns.
        Returns aggregated suggestions.
        """
        analyses = [self.analyze_filename(f) for f in filenames]

        # Find most common subject
        subjects = [a["detected_subject"] for a in analyses if a["detected_subject"]]
        common_subject = max(set(subjects), key=subjects.count) if subjects else None

        # Find most common work type
        work_types = [a["detected_work_type"] for a in analyses if a["detected_work_type"]]
        common_work_type = max(set(work_types), key=work_types.count) if work_types else None

        # Find earliest deadline
        deadlines = [a["detected_deadline"] for a in analyses if a["detected_deadline"]]
        earliest_deadline = min(deadlines) if deadlines else None

        return {
            "files": analyses,
            "common_subject": common_subject,
            "common_work_type": common_work_type,
            "suggested_deadline": earliest_deadline,
            "total_files": len(filenames),
        }

    async def quick_upload(
        self,
        user_id: int,
        files: List[Tuple[str, bytes, str]],  # (filename, content, file_type)
        subject_name: Optional[str] = None,
        work_type: Optional[str] = None,
        work_number: Optional[int] = None,
        title: Optional[str] = None,
        deadline_date: Optional[datetime] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Quick upload with optional metadata override.
        If metadata not provided, auto-detect from filenames.
        """
        if not files:
            return {"success": False, "error": "No files provided"}

        # Analyze files if metadata not fully provided
        filenames = [f[0] for f in files]
        analysis = self.analyze_multiple(filenames)

        # Use provided values or fall back to detected
        final_subject = subject_name or analysis["common_subject"]
        final_work_type = work_type or analysis["common_work_type"] or "homework"
        final_deadline = deadline_date

        if not final_deadline:
            if analysis["suggested_deadline"]:
                final_deadline = datetime.fromisoformat(analysis["suggested_deadline"])
            else:
                # Default: 7 days from now
                final_deadline = datetime.now() + timedelta(days=7)

        if not final_subject:
            return {
                "success": False,
                "error": "Could not detect subject. Please specify manually.",
                "analysis": analysis,
            }

        # Get or create subject
        subject = await self._get_or_create_subject(user_id, final_subject)

        # Create deadline
        final_title = title
        if not final_title:
            if work_number:
                work_labels = {
                    'lab': 'Лабораторная работа',
                    'practical': 'Практическая работа',
                    'homework': 'Домашнее задание',
                    'test': 'Контрольная работа',
                }
                label = work_labels.get(final_work_type, final_work_type)
                final_title = f"{label} №{work_number}"
            else:
                final_title = analysis["files"][0]["suggested_title"] if analysis["files"] else "Задание"

        deadline = Deadline(
            subject_id=subject.id,
            title=final_title,
            work_type=final_work_type,
            work_number=work_number,
            description=description or "",
            deadline_date=final_deadline,
        )
        self.session.add(deadline)
        await self.session.flush()

        # Save materials
        materials_saved = 0
        subject_dir = os.path.join(MATERIALS_DIR, str(subject.id))
        os.makedirs(subject_dir, exist_ok=True)

        for filename, content, file_type in files:
            try:
                # Generate unique filename
                dest_path = os.path.join(subject_dir, filename)
                counter = 1
                base_name, ext = os.path.splitext(filename)
                while os.path.exists(dest_path):
                    dest_path = os.path.join(subject_dir, f"{base_name}_{counter}{ext}")
                    counter += 1

                # Save file
                with open(dest_path, 'wb') as f:
                    f.write(content)

                # Create material record
                material = Material(
                    subject_id=subject.id,
                    file_name=os.path.basename(dest_path),
                    file_type=file_type,
                    file_path=dest_path,
                )
                self.session.add(material)
                materials_saved += 1
            except Exception as e:
                print(f"Error saving file {filename}: {e}")

        await self.session.commit()

        return {
            "success": True,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "deadline_id": deadline.id,
            "deadline_title": deadline.title,
            "deadline_date": deadline.deadline_date.isoformat(),
            "materials_saved": materials_saved,
            "analysis": analysis,
        }

    async def _get_or_create_subject(self, user_id: int, name: str) -> Subject:
        """Get existing subject or create new one."""
        result = await self.session.execute(
            select(Subject).where(
                Subject.user_id == user_id,
                Subject.name == name
            )
        )
        subject = result.scalar_one_or_none()

        if not subject:
            subject = Subject(user_id=user_id, name=name)
            self.session.add(subject)
            await self.session.flush()

        return subject
