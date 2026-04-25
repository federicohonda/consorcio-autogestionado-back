from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal


class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "business-outline"
    m2: int = Field(default=0, description="Metros cuadrados de la unidad del creador")

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del consorcio es requerido")
        return v.strip()
    
    @field_validator("m2")
    @classmethod
    def check_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Los metros cuadrados no pueden ser negativos")
        return v


class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: str
    member_count: int
    admin_name: Optional[str] = None
    your_role: Optional[str] = None
    invite_code: Optional[str] = None



class JoinGroupRequest(BaseModel):
    invite_code: str = Field(alias="inviteCode")
    m2: int = Field(default=0, description="Metros cuadrados de la unidad")

    @field_validator("m2")
    @classmethod
    def check_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Los metros cuadrados deben ser mayores a 0")
        return v


class MemberResponse(BaseModel):
    user_id: int
    full_name: Optional[str]
    role: str
    joined_at: datetime
    m2: int = 0


class TransferRoleRequest(BaseModel):
    newAdminUserId: int


class UserM2Input(BaseModel):
    user_id: int = Field(alias="userId")
    m2: int

    @field_validator("m2")
    @classmethod
    def check_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Los metros cuadrados no pueden ser negativos")
        return v

class UpdateM2Request(BaseModel):
    members: List[UserM2Input]
