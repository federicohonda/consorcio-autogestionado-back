from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PozoMovementResponse(BaseModel):
    id: int
    type: str
    amount: Decimal
    description: Optional[str] = None
    user_name: Optional[str] = None
    created_at: datetime


class PozoResponse(BaseModel):
    balance: Decimal
    monthly_contribution: Decimal
    active_month: int
    movements: list[PozoMovementResponse]


class UpdatePozoConfigRequest(BaseModel):
    monthly_contribution: Decimal = Field(ge=0)


class AdvanceMonthResponse(BaseModel):
    active_month: int
    distributed_amount: Decimal
    beneficiaries_count: int
    new_balance: Decimal
    message: str
