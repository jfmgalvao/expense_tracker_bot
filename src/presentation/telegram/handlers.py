import logging
from telegram import Update
from telegram.ext import ContextTypes
from src.config.settings import settings
from src.application.services import ExpenseService

logger = logging.getLogger(__name__)

class ExpenseTelegramHandler:
    def __init__(self, expense_service: ExpenseService):
        self.expense_service = expense_service

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        # Authorization check
        if settings.allowed_chat_ids and chat_id not in settings.allowed_chat_ids:
            logger.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
            await update.message.reply_text("⛔ Acesso não autorizado a este bot financeiro.")
            return

        raw_message = update.message.text
        if not raw_message:
            return

        try:
            expense = self.expense_service.register_expense(raw_message)
            
            await update.message.reply_text(
                f"✅ **Despesa Registrada!**\n\n"
                f"🧾 **ID:** `#{expense.id}`\n"
                f"💰 **Valor:** `R$ {expense.amount:.2f}`\n"
                f"💳 **Método:** `{expense.payment_method}`\n"
                f"🏷️ **Categoria:** `{expense.category}`\n"
                f"📆 **Referência:** `{expense.reference}`\n"
                f"📝 **Descrição:** `{expense.description}`\n"
                f"📌 **Status:** `{expense.status}`",
                parse_mode="Markdown"
            )
            logger.info(f"Expense {expense.id} registered successfully via Telegram.")
            
        except ValueError as ve:
            await update.message.reply_text(
                f"⚠️ {str(ve)}\n\n"
                f"**Lembrete de Formato:**\n"
                f"`<Valor> <Cartão> <Categoria> <Descrição>`\n"
                f"Ex: `150,50 Nubank Alimentação Mercado`",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            await update.message.reply_text("❌ Ocorreu um erro interno ao registrar a despesa.")
