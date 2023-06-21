from pydantic import EmailStr, BaseModel, Extra, validator
from .mixins import TimeStampMixin, HiddenMixin, NotNullValidatorMixin
from .models.entities import UserInputBase, Role


class UserCreateAdmin(UserInputBase):
    initiative_ids: list[int] | None
    activity_ids: list[int] | None

    class Config:
        title = "UserCreate"
        extra = Extra.forbid


class UserUpdateUserOwner(BaseModel, NotNullValidatorMixin):
    email: EmailStr | None
    first_name: str | None
    last_name: str | None
    biography: str | None

    class Config:
        extra = Extra.forbid
        orm_mode = True

    @validator("email")
    def val_email(cls, value, field):
        return cls.not_null(value, field)


class UserUpdateAdmin(UserUpdateUserOwner, HiddenMixin):
    role: Role | None
    active: bool | None
    initiative_ids: list[int] | None
    activity_ids: list[int] | None

    class Config:
        title = "UserUpdate"
        extra = Extra.forbid

    @validator("role", "active")
    def val_role_active(cls, value, field):
        return cls.not_null(value, field)


class UserOutputGuest(BaseModel):
    id: int
    first_name: str | None
    biography: str | None
    role: Role
    image: str | None


class UserOutputUser(UserOutputGuest):
    last_name: str | None


class UserOutputUserOwner(UserOutputUser):
    pass


class UserOutputActivityOwner(UserOutputUserOwner):
    pass


class UserOutputAdmin(UserOutputActivityOwner, TimeStampMixin, HiddenMixin):
    email: EmailStr | None
    active: bool | None

    class Config:
        title = "UserOutput"


class UserOutputUserList(BaseModel):
    users: list[UserOutputUser]

    class Config:
        orm_mode = True


class UserOutputUserOwnerList(BaseModel):
    users: list[UserOutputUserOwner]

    class Config:
        orm_mode = True


class UserOutputAdminList(BaseModel):
    users: list[UserOutputAdmin]

    class Config:
        title = "UserOutputList"
        orm_mode = True
