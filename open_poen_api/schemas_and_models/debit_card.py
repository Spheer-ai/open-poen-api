from .models.entities import DebitCardBase
from pydantic import BaseModel, Extra
from .mixins import TimeStampMixin


class DebitCardCreateAdmin(DebitCardBase):
    initiative_id: int

    class Config:
        title = "DebitCardCreate"
        extra = Extra.forbid


class DebitCardUpdateAdmin(BaseModel):
    initiative_id: int


class DebitCardOutputActivityOwner(TimeStampMixin):
    id: int
    card_number: str

    class Config:
        title = "DebitCardOutput"


class DebitCardOutputActivityOwnerList(BaseModel):
    debit_cards: list[DebitCardOutputActivityOwner]

    class config:
        orm_mode = True
