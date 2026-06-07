from fastapi import APIRouter, Depends, HTTPException
from src.core.dependencies import get_current_user
from src.repositories.user_repository import find_by_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/recovery-code")
def get_my_recovery_code(current_user: dict = Depends(get_current_user)):
    user = find_by_id(int(current_user["sub"]))
    if not user or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"recovery_code": user.recovery_code}
