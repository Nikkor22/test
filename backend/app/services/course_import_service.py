"""
Course Import Service
Imports course materials from folder structure:
Курс/
    └── Секция (Лекции/Практики/...)/
        └── Название задания/
            ├── _info.txt      ← Dates, description
            ├── _task.json     ← JSON data
            └── файлы...
"""
import os
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Subject, Deadline, Material, Teacher
from app.config import get_settings


settings = get_settings()
MATERIALS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "materials")


class CourseImportService:
    """Service for importing course materials from folder structure."""

    # Map section names to work types
    SECTION_TYPE_MAP = {
        'лекц': 'lecture',
        'лек': 'lecture',
        'практ': 'practical',
        'прак': 'practical',
        'семинар': 'practical',
        'лаб': 'lab',
        'лабораторн': 'lab',
        'курсов': 'coursework',
        'экзамен': 'exam',
        'зачет': 'exam',
        'зачёт': 'exam',
        'контрольн': 'homework',
        'домашн': 'homework',
        'дз': 'homework',
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        os.makedirs(MATERIALS_DIR, exist_ok=True)

    async def import_course(self, user_id: int, course_path: str) -> dict:
        """
        Import a course from folder structure.

        Args:
            user_id: Database user ID
            course_path: Path to the course folder

        Returns:
            Import statistics
        """
        course_path = Path(course_path)
        if not course_path.exists():
            return {"success": False, "error": f"Path not found: {course_path}"}

        stats = {
            "success": True,
            "subjects_created": 0,
            "deadlines_created": 0,
            "materials_imported": 0,
            "errors": [],
        }

        # Course folder name is the subject name
        subject_name = course_path.name
        subject = await self._get_or_create_subject(user_id, subject_name)
        stats["subjects_created"] = 1

        # Iterate through sections (Лекции, Практики, etc.)
        for section_path in course_path.iterdir():
            if not section_path.is_dir():
                continue

            section_name = section_path.name
            work_type = self._detect_work_type(section_name)

            # Iterate through tasks in section
            for task_path in section_path.iterdir():
                if not task_path.is_dir():
                    continue

                try:
                    result = await self._import_task(
                        subject=subject,
                        task_path=task_path,
                        section_name=section_name,
                        work_type=work_type,
                    )
                    stats["deadlines_created"] += result.get("deadline_created", 0)
                    stats["materials_imported"] += result.get("materials_imported", 0)
                except Exception as e:
                    stats["errors"].append(f"Error importing {task_path.name}: {str(e)}")

        await self.session.commit()
        return stats

    async def import_all_courses(self, user_id: int, root_path: str) -> dict:
        """Import all courses from a root directory."""
        root = Path(root_path)
        if not root.exists():
            return {"success": False, "error": f"Path not found: {root_path}"}

        total_stats = {
            "success": True,
            "courses_imported": 0,
            "subjects_created": 0,
            "deadlines_created": 0,
            "materials_imported": 0,
            "errors": [],
        }

        for course_path in root.iterdir():
            if course_path.is_dir() and not course_path.name.startswith('.'):
                result = await self.import_course(user_id, str(course_path))
                if result["success"]:
                    total_stats["courses_imported"] += 1
                    total_stats["subjects_created"] += result["subjects_created"]
                    total_stats["deadlines_created"] += result["deadlines_created"]
                    total_stats["materials_imported"] += result["materials_imported"]
                total_stats["errors"].extend(result.get("errors", []))

        return total_stats

    async def _import_task(
        self,
        subject: Subject,
        task_path: Path,
        section_name: str,
        work_type: str,
    ) -> dict:
        """Import a single task folder."""
        result = {"deadline_created": 0, "materials_imported": 0}

        task_name = task_path.name
        info_file = task_path / "_info.txt"
        json_file = task_path / "_task.json"

        # Parse metadata
        info_data = self._parse_info_file(info_file) if info_file.exists() else {}
        json_data = self._parse_json_file(json_file) if json_file.exists() else {}

        # Merge data (JSON takes precedence)
        task_data = {**info_data, **json_data}

        # Extract deadline date
        deadline_date = self._parse_deadline_date(task_data)
        if not deadline_date:
            # Default to 30 days from now if no date found
            deadline_date = datetime.now()

        # Extract work number from task name (e.g., "Лаб 1", "Практика 2")
        work_number = self._extract_work_number(task_name)

        # Create deadline
        deadline = Deadline(
            subject_id=subject.id,
            title=task_data.get("title", task_name),
            work_type=work_type,
            work_number=work_number,
            description=task_data.get("description", ""),
            deadline_date=deadline_date,
            is_completed=task_data.get("completed", False),
        )
        self.session.add(deadline)
        await self.session.flush()
        result["deadline_created"] = 1

        # Import materials (files in folder)
        for file_path in task_path.iterdir():
            if file_path.is_file() and not file_path.name.startswith('_'):
                try:
                    await self._import_material(subject.id, file_path)
                    result["materials_imported"] += 1
                except Exception as e:
                    print(f"Error importing material {file_path}: {e}")

        # Extract and create teacher if found
        teacher_name = task_data.get("teacher") or task_data.get("преподаватель")
        if teacher_name:
            await self._get_or_create_teacher(subject.id, teacher_name, work_type)

        return result

    def _parse_info_file(self, file_path: Path) -> dict:
        """Parse _info.txt file."""
        data = {}
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.strip().split('\n')

            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    # Map common keys
                    if key in ['дата', 'срок', 'дедлайн', 'deadline', 'date']:
                        data['deadline_str'] = value
                    elif key in ['описание', 'description', 'desc']:
                        data['description'] = value
                    elif key in ['название', 'title', 'name']:
                        data['title'] = value
                    elif key in ['преподаватель', 'teacher', 'препод']:
                        data['teacher'] = value
                    elif key in ['выполнено', 'completed', 'done']:
                        data['completed'] = value.lower() in ['да', 'yes', 'true', '1']
                    else:
                        data[key] = value
                elif not data.get('description'):
                    # First line without : is description
                    data['description'] = line
        except Exception as e:
            print(f"Error parsing info file {file_path}: {e}")

        return data

    def _parse_json_file(self, file_path: Path) -> dict:
        """Parse _task.json file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            return json.loads(content)
        except Exception as e:
            print(f"Error parsing JSON file {file_path}: {e}")
            return {}

    def _parse_deadline_date(self, data: dict) -> Optional[datetime]:
        """Extract deadline date from parsed data."""
        # Try common date fields
        for field in ['deadline', 'deadline_date', 'date', 'срок', 'дата', 'deadline_str']:
            value = data.get(field)
            if value:
                parsed = self._parse_date_string(str(value))
                if parsed:
                    return parsed
        return None

    def _parse_date_string(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats."""
        formats = [
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d.%m.%y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        # Try parsing relative dates
        date_str_lower = date_str.lower()
        if 'сегодня' in date_str_lower or 'today' in date_str_lower:
            return datetime.now()

        return None

    def _detect_work_type(self, section_name: str) -> str:
        """Detect work type from section name."""
        section_lower = section_name.lower()

        for keyword, work_type in self.SECTION_TYPE_MAP.items():
            if keyword in section_lower:
                return work_type

        return "homework"  # Default

    def _extract_work_number(self, name: str) -> Optional[int]:
        """Extract work number from name (e.g., 'Лаб 1' -> 1)."""
        match = re.search(r'(\d+)', name)
        if match:
            return int(match.group(1))
        return None

    async def _import_material(self, subject_id: int, file_path: Path) -> Material:
        """Import a material file."""
        file_name = file_path.name
        file_ext = file_path.suffix.lower().lstrip('.')

        # Map extensions to types
        type_map = {
            'pdf': 'pdf',
            'doc': 'docx',
            'docx': 'docx',
            'xls': 'xlsx',
            'xlsx': 'xlsx',
            'txt': 'txt',
            'ppt': 'pptx',
            'pptx': 'pptx',
        }
        file_type = type_map.get(file_ext, file_ext)

        # Create user materials directory
        subject_dir = os.path.join(MATERIALS_DIR, str(subject_id))
        os.makedirs(subject_dir, exist_ok=True)

        # Copy file to materials directory
        dest_path = os.path.join(subject_dir, file_name)

        # Handle duplicate names
        counter = 1
        base_name = file_path.stem
        while os.path.exists(dest_path):
            dest_path = os.path.join(subject_dir, f"{base_name}_{counter}{file_path.suffix}")
            counter += 1

        shutil.copy2(file_path, dest_path)

        # Create material record
        material = Material(
            subject_id=subject_id,
            file_name=os.path.basename(dest_path),
            file_type=file_type,
            file_path=dest_path,
        )
        self.session.add(material)
        await self.session.flush()

        return material

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

    async def _get_or_create_teacher(
        self, subject_id: int, name: str, work_type: str
    ) -> Teacher:
        """Get existing teacher or create new one."""
        role = "lecturer" if work_type == "lecture" else "practitioner"

        result = await self.session.execute(
            select(Teacher).where(
                Teacher.subject_id == subject_id,
                Teacher.name == name
            )
        )
        teacher = result.scalar_one_or_none()

        if not teacher:
            teacher = Teacher(
                subject_id=subject_id,
                name=name,
                role=role,
            )
            self.session.add(teacher)
            await self.session.flush()

        return teacher
