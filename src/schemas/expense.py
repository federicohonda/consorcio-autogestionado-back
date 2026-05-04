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
    payments: List[PaymentDetail] = Field(default_factory=list)
    paid_by_pozo: bool = Field(default=False, alias="paidByPozo")

    model_config = {"populate_by_name": True}

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
        # Cuando el Pozo paga, no hay pagadores individuales
        if self.paid_by_pozo:
            if self.payments:
                raise ValueError("No se pueden registrar pagadores cuando el gasto es pagado por el Pozo")
            return self
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
    paid_by_user_id: Optional[int]
    created_at: datetime
    category: str = "Otros"
    receipt_url: Optional[str] = None
    paid_by_pozo: bool = False

class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    total_expenses: Decimal
    your_share: Decimal
    you_paid: Decimal
    your_balance: Decimal