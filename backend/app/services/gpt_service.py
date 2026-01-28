import json
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT_PARSE = """Ты помощник студента. Извлеки структурированные данные из заметки.

Извлеки:
1. teacher: {name, subject, temperament, preferences, notes, role} или null
   role: "lecturer" (лектор) или "practitioner" (практикант/семинарист)
2. deadline: {subject, title, work_type, deadline_date, description} или null
   work_type: контрольная/лабораторная/презентация/экзамен/зачет/курсовая/реферат/домашняя работа/тест
   deadline_date: YYYY-MM-DD HH:MM (если время не указано — 23:59)
3. note_type: "note" | "preference" | "tip" | "material"
   - preference = предпочтения препода (что спрашивает, как оценивает)
   - tip = совет по подготовке
   - material = учебный материал
   - note = всё остальное
4. enhanced_description: улучшенная, структурированная версия заметки (1-2 предложения)

JSON формат:
{"teacher":null|{...},"deadline":null|{...},"note_type":"...","enhanced_description":"..."}

Год по умолчанию: 2026."""


SYSTEM_PROMPT_HINT = """Кратко (1-2 предложения) напиши что нужно повторить/выучить для этого дедлайна. Учти заметки и тип работы. Без воды."""

SYSTEM_PROMPT_SUMMARY = """Сделай краткую выжимку по предмету для подготовки. Максимум 200 слов. Структурируй по ключевым темам. Учти заметки и материалы."""

SYSTEM_PROMPT_REMINDER = """Сгенерируй короткое напоминание о дедлайне (2-3 предложения). Включи: что сдавать, когда, что подготовить. Учти характер преподавателя если есть."""

SYSTEM_PROMPT_SEMESTER = """Распарси данные семестра. Извлеки ВСЕ материалы и события.

Формат ответа JSON:
{
  "subjects": [
    {
      "name": "Название предмета",
      "materials": [
        {"type": "lecture|practice|lab|test|exam", "title": "...", "date": "YYYY-MM-DD HH:MM" или null, "description": "краткое описание"}
      ],
      "schedule": [
        {"day_of_week": 0-6, "start_time": "HH:MM", "end_time": "HH:MM", "lesson_type": "lecture|practice|lab", "pair_number": N}
      ],
      "teachers": [
        {"name": "ФИО", "role": "lecturer|practitioner"}
      ]
    }
  ],
  "deadlines": [
    {"subject": "...", "title": "...", "work_type": "...", "deadline_date": "YYYY-MM-DD HH:MM", "description": "..."}
  ]
}

Год по умолчанию: 2026. Извлеки максимум информации."""

SYSTEM_PROMPT_MATERIAL_SUMMARY = """Сделай краткий конспект этого учебного материала (максимум 150 слов). Выдели ключевые понятия, формулы, определения."""


class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _call(self, system: str, user_text: str, temperature: float = 0.3,
                    max_tokens: int = 500, json_mode: bool = True) -> str:
        """Единый метод вызова GPT с минимумом параметров."""
        try:
            kwargs = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT error: {e}")
            return None

    async def parse_note(self, text: str) -> dict:
        """Парсит заметку и извлекает структурированные данные + улучшает описание."""
        result = await self._call(SYSTEM_PROMPT_PARSE, text, max_tokens=600)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        return {"teacher": None, "deadline": None, "note_type": "note", "enhanced_description": text}

    async def generate_deadline_hint(self, deadline_info: str, notes_context: str = "") -> str:
        """Генерирует AI-подсказку для дедлайна: что повторить."""
        context = f"Дедлайн: {deadline_info}"
        if notes_context:
            context += f"\nЗаметки: {notes_context}"
        result = await self._call(SYSTEM_PROMPT_HINT, context, temperature=0.5,
                                  max_tokens=150, json_mode=False)
        return result or ""

    async def generate_subject_summary(self, subject_name: str, materials_text: str, notes_text: str) -> str:
        """Генерирует краткую выжимку по предмету."""
        context = f"Предмет: {subject_name}"
        if materials_text:
            context += f"\nМатериалы:\n{materials_text[:2000]}"
        if notes_text:
            context += f"\nЗаметки:\n{notes_text[:1000]}"
        result = await self._call(SYSTEM_PROMPT_SUMMARY, context, temperature=0.4,
                                  max_tokens=400, json_mode=False)
        return result or ""

    async def generate_reminder(self, deadline_info: dict, teacher_info: dict = None, notes: list = None) -> str:
        """Генерирует текст напоминания."""
        context = f"Предмет: {deadline_info.get('subject', '?')}, Работа: {deadline_info.get('title', '?')}, Тип: {deadline_info.get('work_type', '?')}, Дата: {deadline_info.get('deadline_date', '?')}"
        if deadline_info.get('description'):
            context += f", Описание: {deadline_info['description']}"
        if teacher_info:
            context += f"\nПрепод: {teacher_info.get('name', '?')}"
            if teacher_info.get('temperament'):
                context += f", {teacher_info['temperament']}"
            if teacher_info.get('preferences'):
                context += f", любит: {teacher_info['preferences']}"
        if notes:
            context += f"\nЗаметки: {'; '.join(notes[:3])}"

        result = await self._call(SYSTEM_PROMPT_REMINDER, context, temperature=0.7,
                                  max_tokens=200, json_mode=False)
        if result:
            return result
        return f"Напоминание: {deadline_info.get('title', 'работа')} по {deadline_info.get('subject', '')} — дедлайн {deadline_info.get('deadline_date', 'скоро')}!"

    async def parse_semester_data(self, text: str) -> dict:
        """Парсит данные семестра (расписание, материалы, преподаватели) одним вызовом."""
        result = await self._call(SYSTEM_PROMPT_SEMESTER, text[:4000],
                                  max_tokens=2000, temperature=0.2)
        if result:
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass
        return {"subjects": [], "deadlines": []}

    async def summarize_material(self, title: str, content: str) -> str:
        """Краткий конспект одного учебного материала."""
        text = f"Тема: {title}\n\n{content[:3000]}"
        result = await self._call(SYSTEM_PROMPT_MATERIAL_SUMMARY, text,
                                  temperature=0.3, max_tokens=300, json_mode=False)
        return result or ""
