from abc import ABC, abstractmethod
from src.domain.entities import Expense

class IExpenseRepository(ABC):
    @abstractmethod
    def save(self, expense: Expense) -> int:
        """Saves an expense to the repository and returns its ID."""
        pass
