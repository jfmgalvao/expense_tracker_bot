import io
import re
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository

class ExpenseService:
    def __init__(self, repository: IExpenseRepository):
        self.repository = repository

    def get_user(self, telegram_id: int) -> dict:
        return self.repository.get_user(telegram_id)

    def create_user(self, telegram_id: int, name: str, family_group: str) -> None:
        self.repository.create_user(telegram_id, name, family_group)

    def process_expense_message(self, raw_message: str, family_group: str, user_name: str) -> Expense:
        """
        Faz o parse da mensagem: <Valor> <Cartão> <Categoria> <Descrição>
        Ex: 150 Nubank Alimentação Supermercado
        """
        parts = raw_message.strip().split(" ", 3)
        if len(parts) < 4:
            raise ValueError("Formato inválido. Use: <Valor> <Cartão> <Categoria> <Descrição>")

        amount_str, payment_method, category, description = parts
        amount_str = amount_str.replace(",", ".")
        
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("O valor informado não é numérico válido.")

        # Extract optional reference from the end of description
        reference = datetime.now().strftime("%Y-%m")
        desc_parts = description.split()
        if len(desc_parts) >= 1:
            last_word = desc_parts[-1]
            if re.match(r"^(\d{4}-\d{2})$", last_word):
                reference = last_word
                description = " ".join(desc_parts[:-1]) if len(desc_parts) > 1 else description
            elif re.match(r"^(\d{2}/\d{4})$", last_word):
                month, year = last_word.split("/")
                reference = f"{year}-{month}"
                description = " ".join(desc_parts[:-1]) if len(desc_parts) > 1 else description

        return Expense(
            amount=amount,
            payment_method=payment_method,
            category=category,
            description=description,
            reference=reference,
            family_group=family_group,
            status="PAGO",
            is_fixed=False,
            notes=f"Adicionado por {user_name}"
        )

    def register_expense(self, raw_message: str, family_group: str, user_name: str) -> Expense:
        expense = self.process_expense_message(raw_message, family_group, user_name)
        expense_id = self.repository.save(expense)
        expense.id = expense_id
        return expense

    def get_monthly_summary(self, family_group: str, reference: str = None) -> dict:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_monthly_summary(reference, family_group)
        
    def get_expenses_by_payment_method(self, family_group: str, reference: str = None) -> dict:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_expenses_by_payment_method(reference, family_group)

    def get_card_expenses_details(self, card_name: str, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_card_expenses_details(card_name, reference, family_group)

    def get_all_expenses_by_month(self, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_all_expenses_by_month(reference, family_group)

    def get_recent_expenses(self, family_group: str, limit: int = 10) -> list:
        return self.repository.get_recent_expenses(family_group, limit)
        
    def get_income_vs_expense_chart(self, family_group: str, reference: str = None) -> io.BytesIO:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
            
        summary = self.repository.get_monthly_summary(reference, family_group)
        expenses = summary['total_expenses']
        incomes = summary['total_revenues']
        
        if expenses == 0 and incomes == 0:
            return None
            
        plt.figure(figsize=(8, 8))
        labels = ['Despesas', 'Receitas']
        sizes = [expenses, incomes]
        colors = ['#e74c3c', '#2ecc71']
        
        labels = [l for l, s in zip(labels, sizes) if s > 0]
        colors = [c for c, s in zip(colors, sizes) if s > 0]
        sizes = [s for s in sizes if s > 0]
        
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 14})
        plt.title(f"Balanço: Despesas vs Receitas - {reference}", fontsize=16)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf

    def get_monthly_chart(self, family_group: str, reference: str = None) -> io.BytesIO:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        data = self.repository.get_expenses_by_category(reference, family_group)
        
        if not data:
            return None
            
        categories = list(data.keys())
        amounts = list(data.values())
        
        plt.figure(figsize=(10, 6))
        sns.barplot(x=amounts, y=categories, palette="viridis")
        plt.title(f"Despesas por Categoria - {reference}", fontsize=16)
        plt.xlabel("Valor (R$)", fontsize=12)
        plt.ylabel("Categoria", fontsize=12)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
