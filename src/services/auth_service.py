from src.core.exceptions import AppError
from src.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from src.core.logger import logger
from src.repositories.user_repository import find_by_email, find_by_id, create_user, update_password, find_by_email_and_recovery_code
from src.schemas.user import RegisterRequest, LoginRequest, TokenResponse, AccessTokenResponse, ResetPasswordRequest


def register_user(dto: RegisterRequest) -> TokenResponse:
    if find_by_email(dto.email):
        logger.warning(f"Registration rejected — email already in use: {dto.email}")
        raise AppError(409, "Email already in use")

    hashed = hash_password(dto.password)
    user = create_user(dto.email, hashed, dto.full_name, dto.recovery_code)

    access_token = create_access_token(str(user.id), "resident")
    refresh_token = create_refresh_token(str(user.id))

    logger.info(f"User registered: id={user.id}, email={user.email}")
    return TokenResponse(accessToken=access_token, refreshToken=refresh_token)


def login_user(dto: LoginRequest) -> TokenResponse:
    user = find_by_email(dto.email)
    if not user or not user.hashed_password or not verify_password(dto.password, user.hashed_password):
        logger.warning(f"Login failed — invalid credentials: {dto.email}")
        raise AppError(401, "Invalid email or password")

    if not user.is_active or user.is_blocked:
        raise AppError(403, "Cuenta inactiva o bloqueada")

    role = "admin" if user.is_admin else "resident"
    access_token = create_access_token(str(user.id), role)
    refresh_token = create_refresh_token(str(user.id))

    logger.info(f"User logged in: id={user.id}, role={role}")
    return TokenResponse(accessToken=access_token, refreshToken=refresh_token, full_name=user.full_name)


def reset_password_with_code(dto: ResetPasswordRequest) -> None:
    user = find_by_email_and_recovery_code(dto.email, dto.recovery_code)
    if not user:
        raise AppError(400, "El mail y/o el codigo introducidos son incorrectos, intentelo nuevamente")

    if not user.is_active or user.is_blocked:
        raise AppError(400, "El mail y/o el codigo introducidos son incorrectos, intentelo nuevamente")

    hashed = hash_password(dto.new_password)
    update_password(user.id, hashed)
    logger.info(f"Password reset via recovery code: user_id={user.id}")


def refresh_access_token(refresh_token: str) -> AccessTokenResponse:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise AppError(401, "Refresh token inválido o expirado")

    if payload.get("type") != "refresh":
        raise AppError(401, "Token inválido")

    user = find_by_id(int(payload["sub"]))
    if not user or not user.is_active or user.is_blocked:
        raise AppError(401, "Usuario no encontrado o inactivo")

    role = "admin" if user.is_admin else "resident"
    access_token = create_access_token(str(user.id), role)

    logger.debug(f"Access token refreshed: id={user.id}")
    return AccessTokenResponse(accessToken=access_token)
