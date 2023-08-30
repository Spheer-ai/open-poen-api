from pydantic import BaseModel, Field
from datetime import datetime
from .mixins import TransactionAmount
from ..models import Route, PaymentType
from typing import Literal


class PaymentRead(BaseModel):
    id: int
    booking_date: datetime
    transaction_amount: TransactionAmount
    creditor_name: str
    creditor_account: str
    debtor_name: str
    debtor_account: str
    route: Route
    type: PaymentType
    remittance_information_unstructured: str
    remittance_information_structured: str
    short_user_description: str
    long_user_description: str
    # TODO: Add more fields from other entities such as initiative name,
    # activity name, bank account IBAN, etc.


class BasePaymentCreate(BaseModel):
    booking_date: datetime
    transaction_amount: TransactionAmount
    creditor_name: str
    creditor_account: str
    debtor_name: str
    debtor_account: str
    route: Route
    type: Literal[PaymentType.MANUAL] = Field(default=PaymentType.MANUAL.value)
    short_user_description: str
    long_user_description: str


class PaymentCreate(BasePaymentCreate):
    initiative_id: int
    activity_id: int | None


class PaymentUpdate(BaseModel):
    booking_date: datetime
    transaction_amount: TransactionAmount
    creditor_name: str
    creditor_account: str
    debtor_name: str
    debtor_account: str
    route: Route
    short_user_description: str
    long_user_description: str


class PaymentInitiativeUpdate(BaseModel):
    initiative_id: int


class PaymentActivityUpdate(BaseModel):
    initiative_id: int
    activity_id: int


class PaymentReadList(BaseModel):
    payments: list[PaymentRead]
