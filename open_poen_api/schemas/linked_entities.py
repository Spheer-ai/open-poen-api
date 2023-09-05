from .initiative import InitiativeRead
from .activity import ActivityRead
from .user import UserRead
from .funder import FunderRead
from .regulation import RegulationRead
from .debit_card import DebitCardRead
from .grant import GrantRead
from .bank_account import BankAccountRead
from pydantic import validator


class FunderReadLinked(FunderRead):
    regulations: list[RegulationRead]

    @validator("regulations", pre=True)
    def apply_operation(cls, v):
        return list(v)


class RegulationReadLinked(RegulationRead):
    grant_officers: list[UserRead]
    policy_officers: list[UserRead]
    grants: list[GrantRead]
    funder: FunderRead


class GrantReadLinked(GrantRead):
    regulation: RegulationRead
    initiatives: list[InitiativeRead]
    overseer: UserRead | None


class InitiativeReadLinked(InitiativeRead):
    grant: GrantRead
    initiative_owners: list[UserRead]
    activities: list[ActivityRead]
    debit_cards: list[DebitCardRead] | None

    @validator("initiative_owners", "activities", "debit_cards", pre=True)
    def apply_operation(cls, v):
        return list(v)


class ActivityReadLinked(ActivityRead):
    activity_owners: list[UserRead]
    initiative: InitiativeRead

    @validator("activity_owners", pre=True)
    def apply_operation(cls, v):
        return list(v)


class UserReadLinked(UserRead):
    initiatives: list[InitiativeRead]
    activities: list[ActivityRead]
    user_bank_accounts: list[BankAccountRead]
    owner_bank_accounts: list[BankAccountRead]
    grant_officer_regulations: list[RegulationRead]
    policy_officer_regulations: list[RegulationRead]
    grants: list[GrantRead]

    @validator("initiatives", "activities", pre=True)
    def apply_operation(cls, v):
        return list(v)


class BankAccountReadLinked(BankAccountRead):
    users: list[UserRead]
    owner: UserRead
