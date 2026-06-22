import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    telegram_token: str
    database_url: str
    allowed_chat_ids: set[int]

def get_settings() -> Settings:
    token = os.getenv("TELEGRAM_TOKEN", "")
    db_url = os.getenv("DATABASE_URL", "")
    allowed_ids_str = os.getenv("ALLOWED_CHAT_IDS", "")
    
    allowed_ids = set()
    if allowed_ids_str:
        try:
            allowed_ids = {int(chat_id.strip()) for chat_id in allowed_ids_str.split(",") if chat_id.strip()}
        except ValueError:
            logging.error("Invalid ALLOWED_CHAT_IDS format. Expected comma-separated integers.")
    
    return Settings(
        telegram_token=token,
        database_url=db_url,
        allowed_chat_ids=allowed_ids
    )

settings = get_settings()
