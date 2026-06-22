import io
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository

class ExpenseService:
    def __init__(self, repository: IExpenseRepository):
        self.repository = repository

    def process_expense_message(self, raw_message: str) -> Expense:
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

        # Pega o ano e mês atual no formato YYYY-MM para o campo reference
        current_reference = datetime.now().strftime("%Y-%m")

        return Expense(
            amount=amount,
            payment_method=payment_method,
            category=category,
            description=description,
            reference=current_reference,
            status="PAGO",  # Assumimos pago ao lançar via bot no dia a dia
            is_fixed=False  # Assumimos gasto variável no dia a dia
        )

    def register_expense(self, raw_message: str) -> Expense:
        expense = self.process_expense_message(raw_message)
        expense_id = self.repository.save(expense)
        expense.id = expense_id
        return expense

    def get_monthly_summary(self) -> dict:
        reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_monthly_summary(reference)
        
    def get_expenses_by_payment_method(self) -> dict:
        reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_expenses_by_payment_method(reference)

    def get_recent_expenses(self, limit: int = 10) -> list:
        return self.repository.get_recent_expenses(limit)
        
    def get_monthly_chart(self) -> io.BytesIO:
        reference = datetime.now().strftime("%Y-%m")
        data = self.repository.get_expenses_by_category(reference)
        
        # If no data, return None
        if not data:
            return None
            
        categories = list(data.keys())
        amounts = list(data.values())
        
        # Create chart
        plt.figure(figsize=(10, 6))
        sns.barplot(x=amounts, y=categories, palette="viridis")
        plt.title(f"Despesas por Categoria - {reference}", fontsize=16)
        plt.xlabel("Valor (R$)", fontsize=12)
        plt.ylabel("Categoria", fontsize=12)
        plt.tight_layout()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        return buf
