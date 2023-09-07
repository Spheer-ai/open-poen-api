from pydantic import BaseModel, condecimal
from .mixins import NotNullValidatorMixin, Budget, TransactionAmount


class GrantRead(BaseModel):
    id: int
    name: str
    reference: str
    budget: Budget
    income: TransactionAmount
    expenses: TransactionAmount

    class Config:
        orm_mode = True


class GrantReadList(BaseModel):
    grants: list[GrantRead]

    class Config:
        orm_mode = True


class GrantCreate(BaseModel):
    name: str
    reference: str
    budget: Budget


class GrantOverseerUpdate(BaseModel):
    user_ids: list[int]


class GrantUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = ["name", "reference", "budget"]

    name: str | None
    reference: str | None
    budget: Budget | None
