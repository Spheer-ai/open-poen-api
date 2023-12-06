from pydantic import BaseModel, Field, validator
from datetime import datetime
from .mixins import TransactionAmount
from ..models import Route, PaymentType
from typing import Literal


class PaymentReadUser(BaseModel):
    id: int
    booking_date: datetime
    initiative_id: int | None
    initiative_name: str | None
    activity_id: int | None
    activity_name: str | None
    creditor_name: str | None
    short_user_description: str | None
    iban: str | None
    transaction_amount: TransactionAmount
    linkable_initiative: bool
    linkable_activity: bool


class BasePaymentCreate(BaseModel):
    booking_date: datetime
    transaction_amount: TransactionAmount
    creditor_name: str = Field(max_length=128)
    creditor_account: str = Field(max_length=128)
    debtor_name: str = Field(max_length=128)
    debtor_account: str = Field(max_length=128)
    route: Route
    short_user_description: str = Field(max_length=128)
    long_user_description: str = Field(max_length=512)
    hidden: bool = Field(default=False)


class PaymentCreateManual(BasePaymentCreate):
    type: Literal[PaymentType.MANUAL] = Field(default=PaymentType.MANUAL.value)
    initiative_id: int
    activity_id: int | None


class PaymentCreateAll(BasePaymentCreate):
    type: PaymentType
    initiative_id: int | None
    activity_id: int | None
    debit_card_id: int | None
    bank_account_id: int | None

    @validator("initiative_id", pre=True, always=True)
    def validate_initiative_id(cls, initiative_id, values):
        if values.get("type") == PaymentType.MANUAL and initiative_id is None:
            raise ValueError("initiative_id must be provided when type is 'handmatig'.")
        return initiative_id

    @validator("bank_account_id", pre=True, always=True)
    def validate_bank_account_id(cls, bank_account_id, values):
        if values.get("type") == PaymentType.GOCARDLESS and bank_account_id is None:
            raise ValueError(
                "bank_account_id must be provided when type is 'GoCardless'."
            )
        return bank_account_id

    @validator("debit_card_id", pre=True, always=True)
    def validate_debit_card_id(cls, debit_card_id, values):
        if values.get("type") == PaymentType.BNG and debit_card_id is None:
            raise ValueError("debit_card_id must be provided when type is 'BNG'.")
        return debit_card_id


class PaymentUpdate(BaseModel):
    booking_date: datetime
    transaction_amount: TransactionAmount
    creditor_name: str = Field(max_length=128)
    creditor_account: str = Field(max_length=128)
    debtor_name: str = Field(max_length=128)
    debtor_account: str = Field(max_length=128)
    route: Route
    short_user_description: str = Field(max_length=128)
    long_user_description: str = Field(max_length=512)
    hidden: bool


class PaymentInitiativeUpdate(BaseModel):
    initiative_id: int | None


class PaymentActivityUpdate(BaseModel):
    initiative_id: int
    activity_id: int | None


class PaymentReadList(BaseModel):
    payments: list[PaymentReadUser]

    class Config:
        orm_mode = True


class PaymentUncoupled(BaseModel):
    message: str
