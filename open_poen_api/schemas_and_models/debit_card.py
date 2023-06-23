from .models.entities import DebitCardBase
from pydantic import BaseModel, Extra
from .mixins import TimeStampMixin


class DebitCardCreateAdmin(DebitCardBase):
    pass

    class Config:
        title = "DebitCardCreate"
        extra = Extra.forbid


class DebitCardUpdateAdmin(BaseModel):
    id: int
    initiative_id: int


class DebitCardOutputActivityOwner(TimeStampMixin):
    card_number: str

    class Config:
        title = "DebitCardOutput"


class DebitCardOutputActivityOwnerList(BaseModel):
    debit_cards: list[DebitCardOutputActivityOwner]

    class config:
        orm_mode = True
