from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CreateOwnerPaymentRequest(BaseModel):
    amount: Decimal
    payment_date: Optional[date] = Field(default_factory=date.today)
    notes: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        return v


class OwnerPaymentResponse(BaseModel):
    id: int
    amount: Decimal
    payment_date: date
    receipt_url: str
    notes: Optional[str] = None
    created_at: datetime


class OwnerBalanceResponse(BaseModel):
    current_month_share: Decimal    # Lo que le corresponde pagar este mes
    net_balance: Decimal            # Balance acumulado: positivo = saldo a favor, negativo = deuda
    amount_due: Decimal             # Monto sugerido a pagar
    bank_alias: Optional[str] = None
    bank_cbu: Optional[str] = None
    bank_account_name: Optional[str] = None


class AdminPaymentResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    amount: Decimal
    payment_date: date
    receipt_url: str
    notes: Optional[str] = None
    created_at: datetime


class UpdateBankDataRequest(BaseModel):
    bank_alias: Optional[str] = Field(default=None, alias="bankAlias")
    bank_cbu: Optional[str] = Field(default=None, alias="bankCbu")
    bank_account_name: Optional[str] = Field(default=None, alias="bankAccountName")

    model_config = {"populate_by_name": True}
