from pydantic import BaseModel
from .mixins import TimeStampMixin
from .models.entities import PaymentBase


class PaymentIn(PaymentBase):
    pass


class PaymentOut(PaymentBase, TimeStampMixin):
    id: int


class PaymentOutList(BaseModel):
    payments: list[PaymentOut]
