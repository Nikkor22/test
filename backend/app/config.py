from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Telegram
    bot_token: str
    webapp_url: str = "http://localhost:5173"

    # OpenAI
    openai_api_key: str

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/teacher_app"

    # App
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
