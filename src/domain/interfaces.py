from abc import ABC, abstractmethod
from src.domain.entities import Expense

class IExpenseRepository(ABC):
    @abstractmethod
    def save(self, expense: Expense) -> Expense:
        """Saves an expense to the repository and returns its ID."""
        pass

    @abstractmethod
    def get_monthly_summary(self, reference: str) -> dict:
        pass

    @abstractmethod
    def get_expenses_by_category(self, reference: str) -> dict:
        pass
