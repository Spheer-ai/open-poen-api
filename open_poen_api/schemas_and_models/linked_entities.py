from .initiative import InitiativeRead
from .user import UserRead
from pydantic import validator


class UserReadLinked(UserRead):
    initiatives: list[InitiativeRead]

    @validator("initiatives", pre=True)
    def apply_operation(cls, v):
        return list(v)


class InitiativeReadLinked(InitiativeRead):
    initiative_owners: list[UserRead]

    @validator("initiative_owners", pre=True)
    def apply_operation(cls, v):
        return list(v)
