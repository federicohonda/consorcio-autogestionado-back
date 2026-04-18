from fastapi import APIRouter, Depends, HTTPException
from src.core.dependencies import get_current_user
from src.repositories.user_repository import find_by_id
from src.schemas.user import OwnProfile, PublicProfile

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=OwnProfile)
def get_me(current_user: dict = Depends(get_current_user)):
    user = find_by_id(int(current_user["sub"]))
    if not user or not user.is_active or user.is_blocked:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.patch("/me")
def update_me(current_user: dict = Depends(get_current_user)):
    # TODO: implement profile update
    pass


@router.post("/me/avatar")
def upload_avatar(current_user: dict = Depends(get_current_user)):
    # TODO: implement avatar upload (Supabase Storage)
    pass


@router.get("/{user_id}/profile", response_model=PublicProfile)
def get_profile(user_id: int):
    user = find_by_id(user_id)
    if not user or user.is_blocked:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
