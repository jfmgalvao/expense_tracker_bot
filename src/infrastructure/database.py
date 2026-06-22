import logging
import psycopg2
from src.config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def get_connection(self):
        try:
            return psycopg2.connect(self.database_url)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
