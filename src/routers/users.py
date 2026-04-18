from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me():
    # TODO: implement — requires JWT auth middleware
    pass


@router.patch("/me")
def update_me():
    # TODO: implement profile update
    pass


@router.post("/me/avatar")
def upload_avatar():
    # TODO: implement avatar upload (Supabase Storage)
    pass


@router.get("/{user_id}/profile")
def get_profile(user_id: str):
    # TODO: implement public profile
    pass
