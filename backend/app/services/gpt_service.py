import json
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """Ты помощник студента. Твоя задача - анализировать заметки пользователя и извлекать структурированную информацию о преподавателях и дедлайнах.

Из каждой заметки извлеки:
1. Информацию о преподавателе (если есть):
   - name: имя/фамилия преподавателя
   - subject: предмет
   - temperament: характер/темперамент (строгий, добрый, нейтральный и т.д.)
   - preferences: что любит спрашивать, на что обращает внимание
   - notes: другие заметки о преподавателе

2. Информацию о дедлайне (если есть):
   - subject: предмет
   - title: название работы
   - work_type: тип работы (контрольная, лабораторная, презентация, экзамен, зачет, курсовая, реферат и т.д.)
   - deadline_date: дата в формате YYYY-MM-DD HH:MM (если время не указано, используй 23:59)
   - description: описание, что нужно подготовить

Отвечай ТОЛЬКО в формате JSON:
{
    "teacher": {
        "name": "...",
        "subject": "...",
        "temperament": "...",
        "preferences": "...",
        "notes": "..."
    } или null,
    "deadline": {
        "subject": "...",
        "title": "...",
        "work_type": "...",
        "deadline_date": "YYYY-MM-DD HH:MM",
        "description": "..."
    } или null
}

Если информации о преподавателе или дедлайне нет, ставь null.
Текущий год: 2025. Если год не указан, используй 2025.
"""


class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url="https://openrouter.ai/api/v1"
        )

    async def parse_note(self, text: str) -> dict:
        """Парсит заметку пользователя и извлекает структурированные данные."""
        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"GPT parsing error: {e}")
            return {"teacher": None, "deadline": None, "error": str(e)}

    async def generate_reminder(self, deadline_info: dict, teacher_info: dict = None, notes: list = None) -> str:
        """Генерирует текст напоминания на основе информации о дедлайне."""
        context = f"""
Дедлайн:
- Предмет: {deadline_info.get('subject', 'Неизвестно')}
- Работа: {deadline_info.get('title', 'Неизвестно')}
- Тип: {deadline_info.get('work_type', 'Неизвестно')}
- Дата: {deadline_info.get('deadline_date', 'Неизвестно')}
- Описание: {deadline_info.get('description', '')}
"""

        if teacher_info:
            context += f"""
Преподаватель:
- Имя: {teacher_info.get('name', 'Неизвестно')}
- Характер: {teacher_info.get('temperament', '')}
- Предпочтения: {teacher_info.get('preferences', '')}
- Заметки: {teacher_info.get('notes', '')}
"""

        if notes:
            context += f"\nДополнительные заметки:\n"
            for note in notes[:5]:  # Берем последние 5 заметок
                context += f"- {note}\n"

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты помощник студента. Сгенерируй короткое и полезное напоминание о приближающемся дедлайне.

Напоминание должно включать:
1. Что за работа и когда сдавать
2. Что нужно подготовить (исходя из типа работы и заметок)
3. Советы по подготовке с учетом характера преподавателя (если есть информация)

Формат: краткий, информативный, без лишней воды. Максимум 3-4 предложения."""
                    },
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=300
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT reminder generation error: {e}")
            return f"Напоминание: {deadline_info.get('title', 'работа')} по предмету {deadline_info.get('subject', '')} - дедлайн {deadline_info.get('deadline_date', 'скоро')}!"
