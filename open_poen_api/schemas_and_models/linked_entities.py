from initiative import InitiativeRead
from user import UserRead


class UserReadLinked(UserRead):
    initiatives: list[InitiativeRead]


class InitiativeReadLinked(InitiativeRead):
    initiative_owners: list[UserRead]
