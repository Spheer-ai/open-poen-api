from pydantic import BaseModel


class DebitCardRead(BaseModel):
    id: int
    card_number: str

    class Config:
        orm_mode = True


class DebitCardReadList(BaseModel):
    debit_cards: list[DebitCardRead]

    class Config:
        orm_mode = True
