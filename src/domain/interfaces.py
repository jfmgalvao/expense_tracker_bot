from abc import ABC, abstractmethod
from src.domain.entities import Expense

class IExpenseRepository(ABC):
    @abstractmethod
    def save(self, expense: Expense) -> int:
        pass

    @abstractmethod
    def delete_expense(self, expense_id: int, family_group: str) -> bool:
        pass

    @abstractmethod
    def update_expense_amount(self, expense_id: int, new_amount: float, family_group: str) -> bool:
        pass

    @abstractmethod
    def get_monthly_summary(self, reference: str, family_group: str) -> dict:
        pass

    @abstractmethod
    def get_expenses_by_category(self, reference: str, family_group: str) -> dict:
        pass

    @abstractmethod
    def get_expenses_by_payment_method(self, reference: str, family_group: str) -> dict:
        pass

    @abstractmethod
    def get_card_expenses_details(self, card_name: str, reference: str, family_group: str) -> list:
        pass

    @abstractmethod
    def get_expenses_by_keyword(self, keyword: str, reference: str, family_group: str) -> list:
        pass

    @abstractmethod
    def get_all_expenses_by_month(self, reference: str, family_group: str) -> list:
        pass

    @abstractmethod
    def get_all_incomes_by_month(self, reference: str, family_group: str) -> list:
        pass

    @abstractmethod
    def get_recent_expenses(self, family_group: str, limit: int = 10) -> list:
        pass

    @abstractmethod
    def get_user(self, telegram_id: int) -> dict:
        pass

    @abstractmethod
    def create_user(self, telegram_id: int, name: str, family_group: str) -> None:
        pass
