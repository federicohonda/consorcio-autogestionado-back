from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_validator


class CreateExpenseRequest(BaseModel):
    description: str
    amount: Decimal
    paidByUserId: int

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La descripción es requerida")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class SplitResponse(BaseModel):
    user_id: int
    full_name: Optional[str]
    amount: Decimal


class ExpenseResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    paid_by_name: Optional[str]
    paid_by_user_id: int
    created_at: datetime
    receipt_url: Optional[str] = None


class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    total_expenses: Decimal
    your_share: Decimal
    you_paid: Decimal
    your_balance: Decimal
