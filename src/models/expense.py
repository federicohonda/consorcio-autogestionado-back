from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Expense:
    id: int
    group_id: int
    description: str
    amount: Decimal
    paid_by_user_id: int
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    receipt_url: Optional[str] = None


@dataclass
class ExpenseSplit:
    id: int
    expense_id: int
    user_id: int
    amount: Decimal


@dataclass
class ExpenseWithPayer:
    id: int
    group_id: int
    description: str
    amount: Decimal
    paid_by_user_id: int
    paid_by_name: Optional[str]
    created_at: datetime
    receipt_url: Optional[str] = None
