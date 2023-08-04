from .initiative import InitiativeRead
from .activity import ActivityRead
from .user import UserRead
from .debit_card import DebitCardRead
from pydantic import validator


class UserReadLinked(UserRead):
    initiatives: list[InitiativeRead]
    activities: list[ActivityRead]

    @validator("initiatives", "activities", pre=True)
    def apply_operation(cls, v):
        return list(v)


class InitiativeReadLinked(InitiativeRead):
    initiative_owners: list[UserRead]
    activities: list[ActivityRead]
    # debit_cards: list[DebitCardRead]

    @validator("initiative_owners", "activities", pre=True)
    def apply_operation(cls, v):
        return list(v)


class ActivityReadLinked(ActivityRead):
    activity_owners: list[UserRead]
    initiative: InitiativeRead

    @validator("activity_owners", pre=True)
    def apply_operation(cls, v):
        return list(v)
