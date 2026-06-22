import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.config.settings import settings
from src.application.services import ExpenseService

logger = logging.getLogger(__name__)

class ExpenseTelegramHandler:
    def __init__(self, expense_service: ExpenseService):
        self.expense_service = expense_service

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /start from {update.effective_chat.id}")
        await update.message.reply_text(
            "👋 Olá! Eu sou o seu Bot Financeiro.\n\n"
            "Para registrar uma despesa, envie a mensagem no formato:\n"
            "<Valor> <Cartão> <Categoria> <Descrição>\n\n"
            "Exemplo: 150 Nubank Alimentação Supermercado"
        )
        await self.handle_menu(update, context)

    async def handle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /menu from {update.effective_chat.id}")
        keyboard = [
            [InlineKeyboardButton("📊 Resumo do Mês", callback_data="resumo_mensal")],
            [InlineKeyboardButton("💳 Gastos por Cartão", callback_data="gastos_cartao")],
            [InlineKeyboardButton("📋 Últimos Gastos", callback_data="ultimos_gastos")],
            [InlineKeyboardButton("📈 Gráfico de Categorias", callback_data="grafico_gastos")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎛️ Menu Principal\nEscolha uma das opções abaixo:",
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        logger.info(f"Received callback: {query.data} from {update.effective_chat.id}")
        await query.answer()

        chat_id = update.effective_chat.id
        if settings.allowed_chat_ids and chat_id not in settings.allowed_chat_ids:
            logger.warning(f"Unauthorized callback from {chat_id}")
            return

        try:
            if query.data == "resumo_mensal":
                summary = self.expense_service.get_monthly_summary()
                text = (
                    f"📊 Resumo do Mês Atual\n\n"
                    f"📉 Despesas: R$ {summary['total_expenses']:.2f}\n"
                    f"📈 Receitas: R$ {summary['total_revenues']:.2f}\n"
                    f"⚖️ Saldo: R$ {summary['balance']:.2f}"
                )
                await query.edit_message_text(text=text)

            elif query.data == "gastos_cartao":
                data = self.expense_service.get_expenses_by_payment_method()
                if not data:
                    await query.edit_message_text("Não há despesas registradas neste mês.")
                    return
                
                text = "💳 Gastos por Cartão (Mês Atual)\n\n"
                for method, amount in data.items():
                    text += f"• {method}: R$ {amount:.2f}\n"
                await query.edit_message_text(text=text)

            elif query.data == "ultimos_gastos":
                recent = self.expense_service.get_recent_expenses(5)
                if not recent:
                    await query.edit_message_text("Nenhuma despesa registrada recentemente.")
                    return
                
                text = "📋 Últimos 5 Gastos\n\n"
                for t in recent:
                    text += f"• {t['date']} - {t['category']} - R$ {t['amount']:.2f}\n  {t['description']} ({t['payment_method']})\n\n"
                await query.edit_message_text(text=text)

            elif query.data == "grafico_gastos":
                await query.edit_message_text("Gerando gráfico, aguarde... ⏳")
                chart_buf = self.expense_service.get_monthly_chart()
                if chart_buf:
                    await context.bot.send_photo(chat_id=chat_id, photo=chart_buf)
                    await query.edit_message_text("Aqui está o gráfico do mês atual!")
                else:
                    await query.edit_message_text("Não há dados suficientes neste mês para gerar um gráfico.")
        except Exception as e:
            logger.error(f"Error in callback {query.data}: {e}")
            await query.edit_message_text("❌ Ocorreu um erro ao processar o relatório.")

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
