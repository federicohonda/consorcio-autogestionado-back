from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

@dataclass
class Expense:
    id: int
    group_id: int
    description: str
    amount: Decimal
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime
    # Nuevos campos V2 + Recibo de Thiago
    category: str
    expense_date: date
    division_type: str
    receipt_url: Optional[str] = None
    paid_by_user_id: Optional[int] = None
    paid_by_pozo: bool = False

@dataclass
class ExpensePayment:
    id: int
    expense_id: int
    user_id: int
    amount_paid: Decimal

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
    created_at: datetime
    paid_by_user_id: Optional[int]
    paid_by_name: str
    # Categoría (nuestra) y Recibo (de Thiago) SIEMPRE AL FINAL por tener defaults
    category: Optional[str] = "Otros"
    receipt_url: Optional[str] = None
    paid_by_pozo: bool = False