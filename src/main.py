import os
import logging
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters
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
    application.add_handler(CommandHandler("iniciar", telegram_handler.handle_iniciar))
    application.add_handler(CommandHandler("menu", telegram_handler.handle_menu))
    application.add_handler(CommandHandler("resumo", telegram_handler.handle_resumo))
    application.add_handler(CommandHandler("cartao", telegram_handler.handle_cartao))
    application.add_handler(CommandHandler("detalhamento", telegram_handler.handle_detalhamento))
    application.add_handler(CommandHandler("balanco", telegram_handler.handle_balanco))
    application.add_handler(CommandHandler("total_gasto", telegram_handler.handle_total_gasto))
    application.add_handler(CommandHandler("fixa", telegram_handler.handle_fixa))
    application.add_handler(CommandHandler("receita", telegram_handler.handle_receita))
    application.add_handler(CommandHandler("receita_fixa", telegram_handler.handle_receita_fixa))
    application.add_handler(CommandHandler("remover", telegram_handler.handle_remover))
    application.add_handler(CommandHandler("ajuda", telegram_handler.handle_ajuda))
    application.add_handler(CommandHandler("help", telegram_handler.handle_ajuda))
    application.add_handler(CallbackQueryHandler(telegram_handler.handle_callback))
    
    # Processa mensagens de texto normais (inserção de gastos)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handler.handle_message)
    )
    
    # Processa comandos desconhecidos (deve ser o último handler de comandos)
    application.add_handler(
        MessageHandler(filters.COMMAND, telegram_handler.handle_unknown_command)
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
            url_path=settings.telegram_token,
            webhook_url=f"{render_url}/{settings.telegram_token}"
        )
    else:
        # Modo Long Polling (Para desenvolvimento local)
        logger.info("Modo Long Polling ativado (Local).")
        application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
