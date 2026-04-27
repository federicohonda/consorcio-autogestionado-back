from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


@dataclass
class OwnerPayment:
    id: int
    group_id: int
    user_id: int
    amount: Decimal
    payment_date: date
    receipt_url: str
    created_at: datetime
    notes: Optional[str] = None
