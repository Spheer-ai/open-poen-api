from pydantic import BaseModel


class PaymentRead(BaseModel):
    pass


class PaymentCreate(BaseModel):
    pass


class PaymentUpdate(BaseModel):
    pass


class PaymentInitiativeUpdate(BaseModel):
    pass


class PaymentActivityUpdate(BaseModel):
    pass


class PaymentReadList(BaseModel):
    payments: list[PaymentRead]
