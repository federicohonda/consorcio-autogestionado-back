from pydantic import BaseModel, EmailStr


# TODO: expand schemas as user stories are implemented

class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str


class UserPublic(UserBase):
    id: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
