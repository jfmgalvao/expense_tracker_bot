import os
import logging
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
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
    
    application.add_handler(CommandHandler("start", telegram_handler.handle_start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handler.handle_message)
    )
    
    # Verifica se está rodando no Render (que injeta o RENDER_EXTERNAL_URL)
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    
    if render_url:
        # Modo Webhook (Para a nuvem - Gratuito no Render Web Services)
        logger.info(f"Modo Webhook ativado. URL: {render_url}")
        port = int(os.environ.get("PORT", "10000"))
        
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{render_url}/{settings.telegram_token}"
        )
    else:
        # Modo Long Polling (Para desenvolvimento local)
        logger.info("Modo Long Polling ativado (Local).")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
