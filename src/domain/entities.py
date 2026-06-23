from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime

class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

@dataclass
class Expense:
    amount: float
    payment_method: str
    description: str
    category: str
    reference: str
    family_group: str
    status: str = "PAGO"
    is_fixed: bool = False
    notes: str = "Added via Telegram"
    transaction_type: TransactionType = TransactionType.EXPENSE
    created_at: Optional[datetime] = None
    id: Optional[int] = None
