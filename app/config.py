# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./rss.db"
    RSS_URL: str = "https://habr.com/ru/rss/hubs/all/updates/"
    BACKGROUND_TASK_INTERVAL: int = 300  # 5 минут
    NATS_URL: str = "nats://localhost:4222"
    NATS_SUBJECT: str = "rss.updates"

    class Config:
        env_file = ".env"

settings = Settings()