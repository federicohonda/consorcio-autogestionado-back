from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class GroupSettings:
    group_id: int
    active_month: int  # YYYYMM
    monthly_contribution: Decimal
    pozo_balance: Decimal
    updated_at: datetime


@dataclass
class PozoMovement:
    id: int
    group_id: int
    type: str
    amount: Decimal
    created_at: datetime
    description: Optional[str] = None
    user_id: Optional[int] = None
    expense_id: Optional[int] = None
