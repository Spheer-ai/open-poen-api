from pydantic import BaseModel, HttpUrl
from .mixins import NotNullValidatorMixin
from decimal import Decimal


class GrantRead(BaseModel):
    id: int
    name: str
    reference: str
    budget: Decimal  # TODO: validate digits

    class Config:
        orm_mode = True


class GrantReadList(BaseModel):
    grants: list[GrantRead]

    class Config:
        orm_mode = True


class GrantCreate(BaseModel):
    name: str
    reference: str
    budget: Decimal  # TODO: validate digits


class GrantUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS = ["name", "reference", "budget"]

    name: str | None
    reference: str | None
    budget: Decimal | None
