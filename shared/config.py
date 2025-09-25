import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    BOT1_TOKEN: str
    BOT2_TOKEN: str
    ADMIN_CHAT_ID: int
    DISCOUNT_CHAT_ID: int
    SECRET_KEY: str
    PASSWORD_SECRET: str
    DATABASE_URL: str
    BOT1_CHAT_ID: int

def get_settings() -> Settings:
    return Settings(
        BOT1_TOKEN=os.getenv("BOT1_TOKEN", ""),
        BOT2_TOKEN=os.getenv("BOT2_TOKEN", ""),
        ADMIN_CHAT_ID=int(os.getenv("ADMIN_CHAT_ID", "0")),
        DISCOUNT_CHAT_ID=int(os.getenv("DISCOUNT_CHAT_ID", "0")),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret"),
        PASSWORD_SECRET=os.getenv("PASSWORD_SECRET", "dev-password-secret"),
        DATABASE_URL=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db"),
        BOT1_CHAT_ID=int(os.getenv("BOT1_CHAT_ID", "0")),
    )