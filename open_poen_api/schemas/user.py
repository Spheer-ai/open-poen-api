from pydantic import EmailStr, BaseModel, Field, validator

from .mixins import NotNullValidatorMixin

from fastapi_users import schemas
from ..models import UserRole
from .profile_picture import ProfilePicture


class UserRead(schemas.BaseUser[int]):
    id: int
    email: EmailStr | None
    first_name: str | None
    last_name: str | None
    biography: str | None
    role: UserRole | None
    hidden: bool | None
    profile_picture: ProfilePicture | None

    class Config:
        orm_mode = True


class UserReadList(BaseModel):
    users: list[UserRead]

    class Config:
        orm_mode = True


class UserCreate(schemas.CreateUpdateDictModel):
    # Intentionally not subclassing schemas.BaseUserCreate, because password
    # is a required field there. We add users by invite only, where they get
    # a random password assigned and a password reset link to change it.
    email: EmailStr
    first_name: str | None = Field(None, max_length=64)
    last_name: str | None = Field(None, max_length=64)
    biography: str | None = Field(None, max_length=512)
    role: UserRole = Field(default=UserRole.USER)
    is_active: bool | None = True
    is_superuser: bool | None = False
    is_verified: bool | None = True
    hidden: bool | None = False


class UserCreateWithPassword(UserCreate):
    password: str = Field(max_length=128)


class UserUpdate(schemas.BaseUserUpdate, NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = [
        "role",
        "password",
        "email",
        "is_active",
        "is_superuser",
        "is_verified",
        "hidden",
    ]

    first_name: str | None = Field(max_length=64)
    last_name: str | None = Field(max_length=64)
    biography: str | None = Field(max_length=512)
    role: UserRole | None
    hidden: bool | None
