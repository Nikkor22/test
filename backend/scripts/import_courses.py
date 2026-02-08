#!/usr/bin/env python3
"""
CLI script to import course materials from folder structure.

Usage:
    python scripts/import_courses.py --telegram-id 7167288809 --path /path/to/courses
    python scripts/import_courses.py --telegram-id 7167288809 --path /path/to/course --single

Folder structure expected:
    Курс/
        └── Секция (Лекции/Практики/...)/
            └── Название задания/
                ├── _info.txt      ← Dates, description
                ├── _task.json     ← JSON data
                └── файлы...

_info.txt format:
    Дата: 2024-03-15
    Описание: Описание задания
    Преподаватель: Иванов И.И.

_task.json format:
    {
        "title": "Лабораторная работа 1",
        "deadline": "2024-03-15",
        "description": "Описание",
        "teacher": "Иванов И.И.",
        "completed": false
    }
"""
import os
import sys
import asyncio
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.models.base import async_session, init_db
from app.models import User
from app.services.course_import_service import CourseImportService


async def get_or_create_user(telegram_id: int) -> User:
    """Get user by telegram_id or create if not exists."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created new user with telegram_id: {telegram_id}")

        return user


async def import_courses(telegram_id: int, path: str, single: bool = False):
    """Import courses from folder structure."""
    # Initialize database
    await init_db()

    # Get user
    user = await get_or_create_user(telegram_id)
    print(f"Importing for user: {user.id} (telegram_id: {telegram_id})")
    print(f"Path: {path}")
    print(f"Mode: {'Single course' if single else 'All courses in folder'}")
    print("-" * 50)

    async with async_session() as session:
        import_service = CourseImportService(session)

        if single:
            result = await import_service.import_course(user.id, path)
        else:
            result = await import_service.import_all_courses(user.id, path)

    # Print results
    print("\nImport Results:")
    print("-" * 50)
    if result.get("success"):
        if "courses_imported" in result:
            print(f"Courses imported: {result['courses_imported']}")
        print(f"Subjects created: {result['subjects_created']}")
        print(f"Deadlines created: {result['deadlines_created']}")
        print(f"Materials imported: {result['materials_imported']}")

        if result.get("errors"):
            print(f"\nWarnings/Errors ({len(result['errors'])}):")
            for error in result["errors"][:10]:  # Show first 10
                print(f"  - {error}")
            if len(result["errors"]) > 10:
                print(f"  ... and {len(result['errors']) - 10} more")

        print("\nImport completed successfully!")
    else:
        print(f"Import failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Import course materials from folder structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Import all courses from a folder:
    python scripts/import_courses.py --telegram-id 7167288809 --path /path/to/courses

  Import a single course:
    python scripts/import_courses.py --telegram-id 7167288809 --path /path/to/course --single

Folder structure:
  Курс/
      └── Секция (Лекции/Практики/...)/
          └── Название задания/
              ├── _info.txt
              ├── _task.json
              └── материалы...
        """
    )

    parser.add_argument(
        "--telegram-id", "-t",
        type=int,
        required=True,
        help="Telegram user ID"
    )

    parser.add_argument(
        "--path", "-p",
        type=str,
        required=True,
        help="Path to course folder or root folder with courses"
    )

    parser.add_argument(
        "--single", "-s",
        action="store_true",
        help="Import single course (default: import all courses in folder)"
    )

    args = parser.parse_args()

    # Validate path
    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)

    if not os.path.isdir(args.path):
        print(f"Error: Path is not a directory: {args.path}")
        sys.exit(1)

    # Run import
    asyncio.run(import_courses(args.telegram_id, args.path, args.single))


if __name__ == "__main__":
    main()
