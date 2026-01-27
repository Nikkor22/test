import json
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """Ты помощник студента. Твоя задача - анализировать заметки пользователя и извлекать структурированную информацию о преподавателях и дедлайнах.

Из каждой заметки извлеки:
1. Информацию о преподавателе (если есть):
   - name: имя/фамилия преподавателя
   - subject: предмет
   - role: роль (lecturer - лектор, practitioner - практикант/семинарист)
   - temperament: характер/темперамент (строгий, добрый, нейтральный и т.д.)
   - preferences: что любит спрашивать, на что обращает внимание
   - peculiarities: особенности (опаздывает, отпускает раньше, и т.д.)
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
        "role": "lecturer" или "practitioner",
        "temperament": "...",
        "preferences": "...",
        "peculiarities": "...",
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
Если не понятно лектор или практикант, по умолчанию ставь "lecturer".
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

    async def generate_deadline_description(self, deadline_info: dict, teacher_info: dict = None, notes: list = None) -> str:
        """Генерирует расширенное описание дедлайна с рекомендациями что учить."""
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
- Роль: {teacher_info.get('role', 'Неизвестно')}
- Характер: {teacher_info.get('temperament', '')}
- Предпочтения: {teacher_info.get('preferences', '')}
- Особенности: {teacher_info.get('peculiarities', '')}
"""

        if notes:
            context += f"\nЗаметки по предмету:\n"
            for note in notes[:5]:
                context += f"- {note}\n"

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты помощник студента. Сгенерируй краткое описание что нужно подготовить к данному дедлайну.

На основе типа работы, предмета, информации о преподавателе и заметок, напиши:
1. Что конкретно нужно подготовить
2. На что обратить внимание (учитывая преподавателя)
3. Ключевые темы для повторения

Формат: краткий, 2-3 предложения. Без воды."""
                    },
                    {"role": "user", "content": context}
                ],
                temperature=0.5,
                max_tokens=200
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT description generation error: {e}")
            return ""

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
- Особенности: {teacher_info.get('peculiarities', '')}
"""

        if notes:
            context += f"\nДополнительные заметки:\n"
            for note in notes[:5]:
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

    async def generate_subject_summary(self, subject_name: str, materials_text: list, notes_text: list) -> str:
        """Генерирует краткую выжимку по предмету на основе материалов и заметок."""
        context = f"Предмет: {subject_name}\n\n"

        if materials_text:
            context += "Материалы лекций:\n"
            for i, text in enumerate(materials_text[:10], 1):
                context += f"\n--- Материал {i} ---\n{text[:500]}\n"

        if notes_text:
            context += "\nЗаметки студента:\n"
            for note in notes_text[:10]:
                context += f"- {note}\n"

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты помощник студента. На основе материалов лекций и заметок студента, создай краткую выжимку по предмету.

Выжимка должна включать:
1. Основные темы и концепции предмета
2. Ключевые моменты из лекций
3. Важные определения и формулы (если есть)
4. Что чаще всего спрашивают (если видно из заметок)

Формат: структурированный текст, 5-10 пунктов. Максимум 500 слов."""
                    },
                    {"role": "user", "content": context}
                ],
                temperature=0.5,
                max_tokens=800
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT summary generation error: {e}")
            return f"Не удалось сгенерировать выжимку по предмету {subject_name}."

    async def generate_smart_advert(self, deadline_info: dict, teacher_info: dict = None, subject_notes: list = None) -> str:
        """Генерирует умное уведомление с рекомендациями что учить."""
        context = f"""
Приближающийся дедлайн:
- Предмет: {deadline_info.get('subject', 'Неизвестно')}
- Работа: {deadline_info.get('title', 'Неизвестно')}
- Тип: {deadline_info.get('work_type', 'Неизвестно')}
- Дата: {deadline_info.get('deadline_date', 'Неизвестно')}
- Описание: {deadline_info.get('description', '')}
- GPT-описание: {deadline_info.get('gpt_description', '')}
"""

        if teacher_info:
            context += f"""
Преподаватель:
- Имя: {teacher_info.get('name', 'Неизвестно')}
- Характер: {teacher_info.get('temperament', '')}
- Предпочтения: {teacher_info.get('preferences', '')}
- Особенности: {teacher_info.get('peculiarities', '')}
"""

        if subject_notes:
            context += "\nЗаметки по предмету:\n"
            for note in subject_notes[:5]:
                context += f"- {note}\n"

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты помощник студента. Сгенерируй умное уведомление-адверт для студента.

Уведомление должно:
1. Кратко напомнить о дедлайне
2. Дать конкретные рекомендации что учить/повторить
3. Учесть особенности преподавателя
4. Мотивировать, но без пафоса

Формат: дружелюбный, краткий, 3-5 предложений. Используй эмодзи умеренно."""
                    },
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=300
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT advert generation error: {e}")
            return f"Не забудь про {deadline_info.get('title', 'работу')} по {deadline_info.get('subject', 'предмету')}!"
