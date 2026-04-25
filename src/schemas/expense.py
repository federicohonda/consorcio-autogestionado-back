from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator

class PaymentDetail(BaseModel):
    user_id: int = Field(alias="userId")
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El monto del pago debe ser mayor a 0")
        return v

class CreateExpenseRequest(BaseModel):
    description: str
    amount: Decimal
    category: str = "Otros"
    expense_date: Optional[date] = Field(default_factory=date.today, alias="expenseDate")
    division_type: str = Field(default="EQUALLY", alias="divisionType")
    receipt_url: Optional[str] = Field(default=None, alias="receiptUrl")
    payments: List[PaymentDetail]

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

    @model_validator(mode='after')
    def check_payments_sum(self) -> 'CreateExpenseRequest':
        # Validar que la suma de lo que pagaron coincida con el total del gasto
        total_payments = sum(p.amount for p in self.payments)
        if total_payments != self.amount:
            raise ValueError(f"La suma de los pagos ({total_payments}) debe ser igual al monto total ({self.amount})")
        return self

class SplitResponse(BaseModel):
    user_id: int
    full_name: Optional[str]
    amount: Decimal

class ExpenseResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    paid_by_name: Optional[str]
    paid_by_user_id: Optional[int] # Lo cambiamos a Optional por V2
    created_at: datetime
    category: str = "Otros"
    receipt_url: Optional[str] = None

class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    total_expenses: Decimal
    your_share: Decimal
    you_paid: Decimal
    your_balance: Decimal