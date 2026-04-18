from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Group:
    id: int
    name: str
    description: Optional[str]
    icon: str
    created_at: datetime
    updated_at: datetime


@dataclass
class GroupMember:
    id: int
    group_id: int
    user_id: int
    role: str
    joined_at: datetime


@dataclass
class GroupWithMeta:
    id: int
    name: str
    description: Optional[str]
    icon: str
    member_count: int
    admin_name: Optional[str]
    created_at: datetime
