import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.config.settings import settings
from src.application.services import ExpenseService

logger = logging.getLogger(__name__)

class ExpenseTelegramHandler:
    def __init__(self, expense_service: ExpenseService):
        self.expense_service = expense_service

    async def get_authenticated_user(self, update: Update) -> dict:
        chat_id = update.effective_chat.id
        user = self.expense_service.get_user(chat_id)
        if not user:
            await update.message.reply_text("⛔ Você não está cadastrado. Envie `/iniciar NOME_DA_FAMILIA` para criar ou entrar em uma conta.", parse_mode="Markdown")
        return user

    async def handle_iniciar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        args = context.args
        if not args:
            await update.message.reply_text("⚠️ Envie o comando com o nome da família. Ex: `/iniciar MINHA_FAMILIA`", parse_mode="Markdown")
            return
            
        family_group = args[0].upper()
        name = update.effective_user.first_name or "Usuario"
        
        user = self.expense_service.get_user(chat_id)
        if user:
            await update.message.reply_text(f"Você já está cadastrado na família {user['family_group']}!")
            return
            
        self.expense_service.create_user(chat_id, name, family_group)
        safe_group_name = family_group.replace('_', '\\_')
        await update.message.reply_text(f"✅ Cadastrado com sucesso na família: *{safe_group_name}*!\n\nAgora você já pode lançar suas despesas e ver relatórios.", parse_mode="Markdown")
        await self.handle_menu(update, context)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received /start from {update.effective_chat.id}")
        user = self.expense_service.get_user(update.effective_chat.id)
        if not user:
            await update.message.reply_text(
                "👋 Olá! Eu sou o seu Bot Financeiro Multi-contas.\n\n"
                "Para começar, você precisa criar ou entrar em uma conta familiar.\n"
                "Envie: `/iniciar NOME_DA_SUA_FAMILIA`\n"
                "Exemplo: `/iniciar SILVA`",
                parse_mode="Markdown"
            )
            return

        await update.message.reply_text(
            f"👋 Olá, {user['name']} da família {user['family_group']}!\n\n"
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
        user = self.expense_service.get_user(chat_id)
        if not user:
            await query.edit_message_text("⛔ Você não está cadastrado. Envie /iniciar NOME_DA_FAMILIA")
            return
            
        family_group = user['family_group']

        try:
            if query.data == "resumo_mensal":
                summary = self.expense_service.get_monthly_summary(family_group)
                text = (
                    f"📊 Resumo do Mês Atual ({family_group})\n\n"
                    f"📉 Despesas: R$ {summary['total_expenses']:.2f}\n"
                    f"📈 Receitas: R$ {summary['total_revenues']:.2f}\n"
                    f"⚖️ Saldo: R$ {summary['balance']:.2f}"
                )
                await query.edit_message_text(text=text)

            elif query.data == "gastos_cartao":
                data = self.expense_service.get_expenses_by_payment_method(family_group)
                if not data:
                    await query.edit_message_text("Não há despesas registradas neste mês.")
                    return
                
                text = "💳 Gastos por Cartão (Mês Atual)\n\n"
                for method, amount in data.items():
                    text += f"• {method}: R$ {amount:.2f}\n"
                await query.edit_message_text(text=text)

            elif query.data == "ultimos_gastos":
                recent = self.expense_service.get_recent_expenses(family_group, 5)
                if not recent:
                    await query.edit_message_text("Nenhuma despesa registrada recentemente.")
                    return
                
                text = "📋 Últimos 5 Gastos\n\n"
                for t in recent:
                    text += f"• {t['date']} - {t['category']} - R$ {t['amount']:.2f}\n  {t['description']} ({t['payment_method']})\n\n"
                await query.edit_message_text(text=text)

            elif query.data == "grafico_gastos":
                await query.edit_message_text("Gerando gráfico, aguarde... ⏳")
                chart_buf = self.expense_service.get_monthly_chart(family_group)
                if chart_buf:
                    await context.bot.send_photo(chat_id=chat_id, photo=chart_buf)
                    await query.edit_message_text("Aqui está o gráfico do mês atual!")
                else:
                    await query.edit_message_text("Não há dados suficientes neste mês para gerar um gráfico.")
        except Exception as e:
            logger.error(f"Error in callback {query.data}: {e}")
            await query.edit_message_text("❌ Ocorreu um erro ao processar o relatório.")

    async def handle_resumo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_authenticated_user(update)
        if not user: return
            
        args = context.args
        reference = None
        if args:
            ref_str = args[0]
            if re.match(r"^(\d{4}-\d{2})$", ref_str):
                reference = ref_str
            elif re.match(r"^(\d{2}/\d{4})$", ref_str):
                month, year = ref_str.split("/")
                reference = f"{year}-{month}"
                
        summary = self.expense_service.get_monthly_summary(user['family_group'], reference)
        text = (
            f"📊 Resumo do Mês ({reference or 'Atual'}) - {user['family_group']}\n\n"
            f"📉 Despesas: R$ {summary['total_expenses']:.2f}\n"
            f"📈 Receitas: R$ {summary['total_revenues']:.2f}\n"
            f"⚖️ Saldo: R$ {summary['balance']:.2f}"
        )
        await update.message.reply_text(text)

    async def handle_cartao(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_authenticated_user(update)
        if not user: return
            
        args = context.args
        if not args:
            await update.message.reply_text("⚠️ Uso correto: /cartao <NomeDoCartao> [MM/AAAA]")
            return
            
        card_name = args[0]
        reference = None
        if len(args) > 1:
            ref_str = args[1]
            if re.match(r"^(\d{4}-\d{2})$", ref_str):
                reference = ref_str
            elif re.match(r"^(\d{2}/\d{4})$", ref_str):
                month, year = ref_str.split("/")
                reference = f"{year}-{month}"
                
        details = self.expense_service.get_card_expenses_details(card_name, user['family_group'], reference)
        if not details:
            await update.message.reply_text(f"Nenhuma despesa encontrada para o cartão '{card_name}' no mês {reference or 'atual'}.")
            return
            
        text = f"💳 Detalhes do Cartão: {card_name} ({reference or 'Mês Atual'})\n\n"
        total = 0
        for t in details:
            text += f"• {t['date']} - {t['category']} - R$ {t['amount']:.2f}\n  {t['description']}\n\n"
            total += t['amount']
        text += f"💰 **Total do Cartão:** R$ {total:.2f}"
        
        await update.message.reply_text(text, parse_mode="Markdown")

    async def handle_detalhamento(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_authenticated_user(update)
        if not user: return
            
        args = context.args
        reference = None
        if args:
            ref_str = args[0]
            if re.match(r"^(\d{4}-\d{2})$", ref_str):
                reference = ref_str
            elif re.match(r"^(\d{2}/\d{4})$", ref_str):
                month, year = ref_str.split("/")
                reference = f"{year}-{month}"
                
        details = self.expense_service.get_all_expenses_by_month(user['family_group'], reference)
        if not details:
            await update.message.reply_text(f"Nenhuma despesa encontrada no mês {reference or 'atual'}.")
            return
            
        text = f"📋 Detalhamento Completo ({reference or 'Mês Atual'})\n\n"
        total = 0
        messages_to_send = []
        for t in details:
            line = f"• {t['date']} - {t['category']} - R$ {t['amount']:.2f} ({t['payment_method']})\n  {t['description']}\n\n"
            if len(text) + len(line) > 3800:
                messages_to_send.append(text)
                text = ""
            text += line
            total += t['amount']
            
        text += f"💰 **Total de Despesas:** R$ {total:.2f}"
        messages_to_send.append(text)
        
        for msg in messages_to_send:
            await update.message.reply_text(msg, parse_mode="Markdown")

    async def handle_balanco(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_authenticated_user(update)
        if not user: return
            
        args = context.args
        reference = None
        if args:
            ref_str = args[0]
            if re.match(r"^(\d{4}-\d{2})$", ref_str):
                reference = ref_str
            elif re.match(r"^(\d{2}/\d{4})$", ref_str):
                month, year = ref_str.split("/")
                reference = f"{year}-{month}"
                
        await update.message.reply_text("Gerando gráfico de balanço, aguarde... ⏳")
        chart_buf = self.expense_service.get_income_vs_expense_chart(user['family_group'], reference)
        if chart_buf:
            await context.bot.send_photo(chat_id=chat_id, photo=chart_buf)
            await update.message.reply_text(f"Aqui está o balanço de {reference or 'este mês'}!")
        else:
            await update.message.reply_text("Não há dados suficientes para gerar o gráfico.")

    async def handle_ajuda(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 *Comandos Disponíveis:*\n\n"
            "🔹 `/iniciar NOME_FAMILIA` - Cadastra-se em uma conta familiar.\n"
            "🔹 `/menu` - Abre os botões interativos.\n"
            "🔹 `/resumo [MM/AAAA]` - Mostra totais de entradas e saídas.\n"
            "🔹 `/detalhamento [MM/AAAA]` - Lista detalhada de todos os gastos.\n"
            "🔹 `/balanco [MM/AAAA]` - Gráfico visual de Receitas x Despesas.\n"
            "🔹 `/cartao NOME [MM/AAAA]` - Detalha faturas do cartão (ex: /cartao nubank).\n"
            "🔹 `/ajuda` - Mostra esta lista de comandos.\n\n"
            "💡 *Para adicionar um gasto ou receita:*\n"
            "Envie uma mensagem de texto simples:\n"
            "👉 `150 Nubank Alimentação Supermercado`"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "❓ Comando não reconhecido.\n"
            "Digite /ajuda para ver a lista de comandos disponíveis."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await self.get_authenticated_user(update)
        if not user: return

        raw_message = update.message.text
        if not raw_message:
            return

        try:
            expense = self.expense_service.register_expense(raw_message, user['family_group'], user['name'])
            
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
