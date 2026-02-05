"""
iCal sync service for importing schedule from MIREA.
Parses iCal feed and updates ScheduleEntry records.
"""
import httpx
import re
from datetime import datetime
from typing import Optional
from icalendar import Calendar
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Subject, ScheduleEntry


class ICalSyncService:
    """Service for syncing schedule from iCal feed."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_ical(self, url: str) -> Optional[str]:
        """Fetch iCal data from URL."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching iCal: {e}")
            return None

    def parse_ical(self, ical_data: str) -> list[dict]:
        """Parse iCal data and extract events."""
        events = []
        try:
            cal = Calendar.from_ical(ical_data)
            for component in cal.walk():
                if component.name == "VEVENT":
                    event = self._parse_event(component)
                    if event:
                        events.append(event)
        except Exception as e:
            print(f"Error parsing iCal: {e}")
        return events

    def _parse_event(self, component) -> Optional[dict]:
        """Parse a single VEVENT component."""
        try:
            summary = str(component.get("SUMMARY", ""))
            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            location = str(component.get("LOCATION", "")) or None
            description = str(component.get("DESCRIPTION", "")) or None

            if not dtstart:
                return None

            dt = dtstart.dt
            if hasattr(dt, 'hour'):
                start_time = dt.strftime("%H:%M")
                day_of_week = dt.weekday()
                event_date = dt.date() if hasattr(dt, 'date') else dt
            else:
                # All-day event, skip
                return None

            if dtend and hasattr(dtend.dt, 'hour'):
                end_time = dtend.dt.strftime("%H:%M")
            else:
                end_time = start_time

            # Parse subject name and class type from summary
            subject_name, class_type = self._parse_summary(summary)

            # Extract teacher name from description
            teacher_name = self._parse_teacher(description) if description else None

            # Calculate week number to determine even/odd
            week_number = event_date.isocalendar()[1]
            week_type = "even" if week_number % 2 == 0 else "odd"

            return {
                "subject_name": subject_name,
                "class_type": class_type,
                "day_of_week": day_of_week,
                "start_time": start_time,
                "end_time": end_time,
                "room": location,
                "teacher_name": teacher_name,
                "week_type": week_type,
                "event_date": event_date,
            }
        except Exception as e:
            print(f"Error parsing event: {e}")
            return None

    def _parse_summary(self, summary: str) -> tuple[str, str]:
        """Parse subject name and class type from summary."""
        # Common patterns: "Математика (лекция)", "Физика (практика)", "Программирование (лаб)"
        class_type = "lecture"

        # Detect class type from keywords
        summary_lower = summary.lower()
        if "лек" in summary_lower:
            class_type = "lecture"
        elif "практ" in summary_lower or "семинар" in summary_lower:
            class_type = "practice"
        elif "лаб" in summary_lower:
            class_type = "lab"

        # Remove class type suffix from subject name
        subject_name = re.sub(r'\s*\([^)]*\)\s*$', '', summary).strip()
        if not subject_name:
            subject_name = summary

        return subject_name, class_type

    def _parse_teacher(self, description: str) -> Optional[str]:
        """Extract teacher name from description."""
        if not description:
            return None

        # Try to find teacher name patterns (e.g., "Преподаватель: Иванов И.И.")
        patterns = [
            r'(?:Преподаватель|Препод|Лектор|Teacher)[:\s]+([^\n,]+)',
            r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.[А-ЯЁ]\.)',  # "Иванов И.И."
            r'([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+)',  # "Иванов Иван Иванович"
        ]

        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()

        return None

    async def sync_user_schedule(self, user: User) -> dict:
        """Sync schedule for a user from their iCal URL."""
        if not user.ical_url:
            return {"success": False, "error": "No iCal URL configured"}

        # Fetch iCal data
        ical_data = await self.fetch_ical(user.ical_url)
        if not ical_data:
            return {"success": False, "error": "Failed to fetch iCal data"}

        # Parse events
        events = self.parse_ical(ical_data)
        if not events:
            return {"success": False, "error": "No events found in iCal"}

        # Group events by unique schedule pattern
        patterns = self._group_events_to_patterns(events)

        # Create/update schedule entries
        created = 0
        updated = 0

        for pattern in patterns:
            # Get or create subject
            subject = await self._get_or_create_subject(user.id, pattern["subject_name"])

            # Check if schedule entry exists
            result = await self.session.execute(
                select(ScheduleEntry).where(
                    ScheduleEntry.subject_id == subject.id,
                    ScheduleEntry.day_of_week == pattern["day_of_week"],
                    ScheduleEntry.start_time == pattern["start_time"],
                    ScheduleEntry.class_type == pattern["class_type"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.end_time = pattern["end_time"]
                existing.room = pattern["room"]
                existing.teacher_name = pattern["teacher_name"]
                existing.week_type = pattern["week_type"]
                updated += 1
            else:
                # Create new
                entry = ScheduleEntry(
                    subject_id=subject.id,
                    day_of_week=pattern["day_of_week"],
                    start_time=pattern["start_time"],
                    end_time=pattern["end_time"],
                    room=pattern["room"],
                    class_type=pattern["class_type"],
                    week_type=pattern["week_type"],
                    teacher_name=pattern["teacher_name"],
                )
                self.session.add(entry)
                created += 1

        # Update user's last sync time
        user.last_schedule_sync = datetime.utcnow()

        await self.session.commit()

        return {
            "success": True,
            "events_parsed": len(events),
            "patterns_found": len(patterns),
            "created": created,
            "updated": updated,
        }

    def _group_events_to_patterns(self, events: list[dict]) -> list[dict]:
        """Group events into unique schedule patterns."""
        patterns = {}

        for event in events:
            # Key: subject + day + time + class_type
            key = (
                event["subject_name"],
                event["day_of_week"],
                event["start_time"],
                event["class_type"],
            )

            if key not in patterns:
                patterns[key] = {
                    "subject_name": event["subject_name"],
                    "day_of_week": event["day_of_week"],
                    "start_time": event["start_time"],
                    "end_time": event["end_time"],
                    "room": event["room"],
                    "class_type": event["class_type"],
                    "teacher_name": event["teacher_name"],
                    "week_types": set(),
                }

            patterns[key]["week_types"].add(event["week_type"])

        # Determine final week_type based on occurrences
        result = []
        for pattern in patterns.values():
            if len(pattern["week_types"]) > 1:
                pattern["week_type"] = "both"
            else:
                pattern["week_type"] = list(pattern["week_types"])[0]
            del pattern["week_types"]
            result.append(pattern)

        return result

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

    async def clear_user_schedule(self, user: User) -> int:
        """Clear all schedule entries for a user."""
        # Get all subject IDs for user
        result = await self.session.execute(
            select(Subject.id).where(Subject.user_id == user.id)
        )
        subject_ids = [row[0] for row in result.fetchall()]

        if not subject_ids:
            return 0

        # Delete all schedule entries for these subjects
        result = await self.session.execute(
            delete(ScheduleEntry).where(ScheduleEntry.subject_id.in_(subject_ids))
        )
        await self.session.commit()

        return result.rowcount
