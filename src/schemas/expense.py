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

class PercentageDetail(BaseModel):
    user_id: int = Field(alias="userId")
    percentage: Decimal

    model_config = {"populate_by_name": True}

    @field_validator("percentage")
    @classmethod
    def percentage_in_range(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        return v


class CreateExpenseRequest(BaseModel):
    description: str
    amount: Decimal
    category: str = "Otros"
    expense_date: Optional[date] = Field(default_factory=date.today, alias="expenseDate")
    division_type: str = Field(default="EQUALLY", alias="divisionType")
    receipt_url: Optional[str] = Field(default=None, alias="receiptUrl")
    payments: List[PaymentDetail] = Field(default_factory=list)
    percentages: List[PercentageDetail] = Field(default_factory=list)
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
        if self.paid_by_pozo:
            if self.payments:
                raise ValueError("No se pueden registrar pagadores cuando el gasto es pagado por el Pozo")
            return self
        if self.division_type == "BY_PERCENTAGE":
            if not self.percentages:
                raise ValueError("Debés indicar los porcentajes de división")
            total_pct = sum(p.percentage for p in self.percentages)
            if abs(total_pct - Decimal("100")) > Decimal("0.01"):
                raise ValueError(f"Los porcentajes deben sumar 100% (suma actual: {total_pct}%)")
        elif self.percentages:
            raise ValueError("Los porcentajes solo aplican para división por porcentaje")
        total_payments = sum(p.amount for p in self.payments)
        if total_payments != self.amount:
            raise ValueError(f"La suma de los pagos ({total_payments}) debe ser igual al monto total ({self.amount})")
        return self

class UpdateExpenseRequest(BaseModel):
    description: str
    amount: Decimal
    category: str = "Otros"
    expense_date: date = Field(default_factory=date.today, alias="expenseDate")
    division_type: str = Field(default="EQUALLY", alias="divisionType")
    payments: List[PaymentDetail] = Field(default_factory=list)
    percentages: List[PercentageDetail] = Field(default_factory=list)

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
    def check_payments_sum(self) -> 'UpdateExpenseRequest':
        if self.division_type == "BY_PERCENTAGE":
            if not self.percentages:
                raise ValueError("Debés indicar los porcentajes de división")
            total_pct = sum(p.percentage for p in self.percentages)
            if abs(total_pct - Decimal("100")) > Decimal("0.01"):
                raise ValueError(f"Los porcentajes deben sumar 100% (suma actual: {total_pct}%)")
        elif self.percentages:
            raise ValueError("Los porcentajes solo aplican para división por porcentaje")
        total_payments = sum(p.amount for p in self.payments)
        if total_payments != self.amount:
            raise ValueError(f"La suma de los pagos ({total_payments}) debe ser igual al monto total ({self.amount})")
        return self


class ExpensePaymentDetail(BaseModel):
    user_id: int
    amount: Decimal


class ExpenseDetailResponse(BaseModel):
    id: int
    description: str
    amount: Decimal
    category: str
    expense_date: date
    division_type: str
    paid_by_pozo: bool
    receipt_url: Optional[str] = None
    created_at: datetime
    payments: List[ExpensePaymentDetail]


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