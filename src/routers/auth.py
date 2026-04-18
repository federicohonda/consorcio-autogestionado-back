from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register():
    # TODO: implement user registration
    pass


@router.post("/login")
def login():
    # TODO: implement user login
    pass


@router.post("/refresh")
def refresh():
    # TODO: implement token refresh
    pass


@router.post("/logout")
def logout():
    # TODO: implement logout
    pass
