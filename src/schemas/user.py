import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    full_name: str = Field(alias="fullName")
    email: EmailStr
    password: str
    recovery_code: str = Field(alias="recoveryCode")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre completo es requerido")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Debe contener al menos una mayúscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("Debe contener al menos una minúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("Debe contener al menos un número")
        return v

    @field_validator("recovery_code")
    @classmethod
    def validate_recovery_code(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("El código de recuperación debe ser de exactamente 6 dígitos")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    recovery_code: str = Field(alias="recoveryCode")
    new_password: str = Field(alias="newPassword")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("recovery_code")
    @classmethod
    def validate_recovery_code(cls, v: str) -> str:
        if not re.fullmatch(r"\d{6}", v):
            raise ValueError("El código de recuperación debe ser de 6 dígitos")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Debe contener al menos una mayúscula")
        if not re.search(r"[a-z]", v):
            raise ValueError("Debe contener al menos una minúscula")
        if not re.search(r"[0-9]", v):
            raise ValueError("Debe contener al menos un número")
        return v


class RefreshRequest(BaseModel):
    refreshToken: str


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    full_name: Optional[str] = None


class AccessTokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"


class OwnProfile(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_blocked: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicProfile(BaseModel):
    id: int
    full_name: Optional[str]
    description: Optional[str]
    avatar_url: Optional[str]

    model_config = ConfigDict(from_attributes=True)
