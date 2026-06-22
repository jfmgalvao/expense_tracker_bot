import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters
from src.config.settings import settings
from src.infrastructure.database import DatabaseConnection
from src.infrastructure.repositories import PostgresExpenseRepository
from src.application.services import ExpenseService
from src.presentation.telegram.handlers import ExpenseTelegramHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN is not configured. Exiting.")
        return
    if not settings.database_url:
        logger.error("DATABASE_URL is not configured. Exiting.")
        return

    # 1. Setup Infrastructure
    db_connection = DatabaseConnection(settings.database_url)
    expense_repo = PostgresExpenseRepository(db_connection)

    # 2. Setup Application Service
    expense_service = ExpenseService(expense_repo)

    # 3. Setup Presentation (Telegram Handlers)
    telegram_handler = ExpenseTelegramHandler(expense_service)

    # 4. Initialize Telegram Bot Application
    logger.info("Starting Telegram Bot Application...")
    application = ApplicationBuilder().token(settings.telegram_token).build()
    
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handler.handle_message)
    )
    
    # 5. Run
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
