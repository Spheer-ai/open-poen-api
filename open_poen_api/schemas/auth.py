from pydantic import BaseModel
from enum import Enum


class AuthActionsRead(BaseModel):
    actions: set[str]


class AuthFieldsRead(BaseModel):
    fields: set[str]


class AuthEntityClass(str, Enum):
    USER = "User"
    FUNDER = "Funder"
    REGULATION = "Regulation"
    GRANT = "Grant"
    BANK_ACCOUNT = "BankAccount"
    INITIATIVE = "Initiative"
    ACTIVITY = "Activity"
    PAYMENT = "Payment"


class LinkableInitiative(BaseModel):
    id: int
    name: str


class LinkableActivity(BaseModel):
    id: int
    name: str


class LinkableInitiatives(BaseModel):
    initiatives: list[LinkableInitiative]


class LinkableActivities(BaseModel):
    activities: list[LinkableActivity]
