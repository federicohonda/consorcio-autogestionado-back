from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "business-outline"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del grupo es requerido")
        return v.strip()


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: str
    member_count: int
    admin_name: Optional[str] = None
    your_role: Optional[str] = None


class MemberResponse(BaseModel):
    user_id: int
    full_name: Optional[str]
    role: str
    joined_at: datetime


class TransferRoleRequest(BaseModel):
    newAdminUserId: int
