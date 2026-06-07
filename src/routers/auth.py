from fastapi import APIRouter, HTTPException
from src.core.exceptions import AppError
from src.schemas.user import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, AccessTokenResponse, ResetPasswordRequest
from src.services.auth_service import register_user, login_user, refresh_access_token, reset_password_with_code

router = APIRouter(prefix="/auth", tags=["auth"])


def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/register", status_code=201, response_model=TokenResponse)
def register(body: RegisterRequest):
    return _handle(register_user, body)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    return _handle(login_user, body)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest):
    return _handle(refresh_access_token, body.refreshToken)


@router.post("/logout")
def logout():
    return {"message": "Sesión cerrada correctamente"}


@router.post("/reset-password", status_code=200)
def reset_password(body: ResetPasswordRequest):
    _handle(reset_password_with_code, body)
    return {"message": "Contraseña actualizada correctamente"}
