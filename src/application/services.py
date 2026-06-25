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

    def process_expense_message(self, raw_message: str, family_group: str, user_name: str, is_fixed: bool = False, transaction_type: str = 'EXPENSE') -> Expense:
        """
        Faz o parse da mensagem suportando formato por vírgula (ideal) ou espaço (legado).
        Ex: 150,50, Conta Corrente, Lazer, Cinema no shopping
        """
        if "," in raw_message:
            raw_parts = [p.strip() for p in raw_message.split(",")]
            parts = []
            if len(raw_parts) >= 2:
                try:
                    # Verifica se a primeira vírgula foi usada como centavos (ex: 150,50)
                    float(f"{raw_parts[0]}.{raw_parts[1]}")
                    parts.append(f"{raw_parts[0]}.{raw_parts[1]}")
                    parts.extend(raw_parts[2:])
                except ValueError:
                    parts = raw_parts
            else:
                parts = raw_parts

            if len(parts) >= 4:
                amount_str = parts[0]
                payment_method = parts[1]
                category = parts[2]
                description = ", ".join(parts[3:])
            else:
                # Fallback para espaço se não encontrou os campos
                parts = raw_message.strip().split(" ", 3)
                if len(parts) < 4:
                    raise ValueError("Formato inválido. Use: Valor, Cartão/Conta, Categoria, Descrição")
                amount_str, payment_method, category, description = parts
        else:
            parts = raw_message.strip().split(" ", 3)
            if len(parts) < 4:
                raise ValueError("Formato inválido. Use: Valor, Cartão/Conta, Categoria, Descrição")
            amount_str, payment_method, category, description = parts

        amount_str = amount_str.replace(",", ".")
        
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("O valor informado não é numérico válido.")

        # Extract optional reference from the end of description
        # Parse pendente status
        status = "PAGO"
        if description.lower().endswith("pendente"):
            status = "PENDENTE"
            # Remove "pendente" from description, keeping anything else
            description = re.sub(r'(?i)[,\s]*pendente$', '', description).strip()
            
            # If the description became empty because they just typed the category and "pendente", fallback
            if not description:
                description = category

        # Reference month mapping (Retroactive)
        ref_match = re.search(r"(\d{2}/\d{4})$", description)
        if ref_match:
            ref_str = ref_match.group(1)
            m, y = ref_str.split("/")
            reference = f"{y}-{m}"
            description = description.replace(ref_str, "").strip(", ")
        else:
            reference = datetime.now().strftime("%Y-%m")

        from src.domain.entities import TransactionType
        return Expense(
            amount=amount,
            payment_method=payment_method,
            description=description,
            category=category,
            reference=reference,
            family_group=family_group,
            status=status,
            notes=f"Adicionado por {user_name}",
            is_fixed=is_fixed,
            transaction_type=TransactionType(transaction_type)
        )

    def register_expense(self, raw_message: str, family_group: str, user_name: str, is_fixed: bool = False, transaction_type: str = 'EXPENSE') -> Expense:
        expense = self.process_expense_message(raw_message, family_group, user_name, is_fixed, transaction_type)
        try:
            expense.id = self.repository.save(expense)
            return expense
        except Exception as e:
            logger.error(f"Failed to save expense: {e}")
            raise Exception("Erro ao salvar no banco de dados.")

    def register_installments(self, raw_message: str, family_group: str, user_name: str) -> list:
        if "," not in raw_message:
            raise ValueError("Use vírgula para separar a Quantidade de Parcelas do resto.")
            
        raw_parts = [p.strip() for p in raw_message.split(",")]
        try:
            installments = int(raw_parts[0])
        except ValueError:
            raise ValueError("O primeiro valor deve ser a quantidade de parcelas (número inteiro).")
            
        if installments <= 0 or installments > 360:
            raise ValueError("Quantidade de parcelas inválida (1 a 360).")

        raw_parts = raw_parts[1:]
        
        parts = []
        if len(raw_parts) >= 2:
            try:
                float(f"{raw_parts[0]}.{raw_parts[1]}")
                parts.append(f"{raw_parts[0]}.{raw_parts[1]}")
                parts.extend(raw_parts[2:])
            except ValueError:
                parts = raw_parts
        else:
            parts = raw_parts

        if len(parts) >= 4:
            amount_str = parts[0]
            payment_method = parts[1]
            category = parts[2]
            description = ", ".join(parts[3:])
        else:
            # Fallback for space
            fallback_str = ", ".join(raw_parts)
            fallback_parts = fallback_str.strip().split(" ", 3)
            if len(fallback_parts) < 4:
                raise ValueError("Formato inválido. Use: QTD, Valor, Cartão/Conta, Categoria, Descrição")
            amount_str, payment_method, category, description = fallback_parts

        amount_str = amount_str.replace(",", ".")
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("O valor informado não é numérico válido.")

        base_date = datetime.now()
        base_month = base_date.month
        base_year = base_date.year
        
        ref_match = re.search(r"(\d{2}/\d{4})$", description)
        if ref_match:
            ref_str = ref_match.group(1)
            m, y = ref_str.split("/")
            base_month = int(m)
            base_year = int(y)
            description = description.replace(ref_str, "").strip(", ")

        expenses = []
        for i in range(installments):
            current_month = base_month + i
            current_year = base_year + ((current_month - 1) // 12)
            current_month = ((current_month - 1) % 12) + 1
            ref_str = f"{current_year}-{current_month:02d}"

            current_desc = f"{description} ({i+1}/{installments})"

            expense = Expense(
                amount=amount,
                payment_method=payment_method,
                description=current_desc,
                category=category,
                reference=ref_str,
                family_group=family_group,
                notes=f"Adicionado por {user_name}",
                is_fixed=False,
                transaction_type=TransactionType.EXPENSE
            )
            expense.id = self.repository.save(expense)
            expenses.append(expense)

        return expenses

    def delete_expense(self, expense_id: int, family_group: str) -> bool:
        return self.repository.delete_expense(expense_id, family_group)

    def update_expense_amount(self, expense_id: int, new_amount: float, family_group: str) -> bool:
        return self.repository.update_expense_amount(expense_id, new_amount, family_group)

    def mark_as_paid(self, expense_id: int, family_group: str) -> bool:
        return self.repository.mark_as_paid(expense_id, family_group)

    def sync_fixed_expenses(self, family_group: str, reference: str = None) -> None:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
            
        # Calcula o mês anterior
        year, month = map(int, reference.split("-"))
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
            
        prev_reference = f"{prev_year}-{prev_month:02d}"
        self.repository.clone_fixed_expenses(family_group, prev_reference, reference)

    def get_monthly_summary(self, family_group: str, reference: str = None) -> dict:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_monthly_summary(reference, family_group)

    def get_portfolio_summary(self, family_group: str) -> list:
        return self.repository.get_portfolio_summary(family_group)
        
    def get_expenses_by_payment_method(self, family_group: str, reference: str = None) -> dict:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_expenses_by_payment_method(reference, family_group)

    def get_card_expenses_details(self, card_name: str, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_card_expenses_details(card_name, reference, family_group)

    def get_expenses_by_keyword(self, keyword: str, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_expenses_by_keyword(keyword, reference, family_group)

    def get_all_expenses_by_month(self, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_all_expenses_by_month(reference, family_group)

    def get_all_incomes_by_month(self, family_group: str, reference: str = None) -> list:
        if not reference:
            reference = datetime.now().strftime("%Y-%m")
        return self.repository.get_all_incomes_by_month(reference, family_group)

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
