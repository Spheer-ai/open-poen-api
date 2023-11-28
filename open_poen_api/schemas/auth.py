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
