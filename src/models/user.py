from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: int
    email: str
    hashed_password: Optional[str]
    full_name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_blocked: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
