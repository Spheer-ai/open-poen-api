from pydantic import BaseModel, Field
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
    name: str = Field(max_length=128)
    reference: str = Field(max_length=128)
    budget: Budget = Field(examples=[1000.01, 555, 9455.11])


class GrantOverseerUpdate(BaseModel):
    user_ids: list[int]


class GrantUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = ["name", "reference", "budget"]

    name: str | None = Field(max_length=128)
    reference: str | None = Field(max_length=128)
    budget: Budget | None
