from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
from decimal import Decimal
from typing import Literal
from ..models import Route, PaymentType


class PaymentAccountInfo(BaseModel):
    iban: str | None


class PaymentTransactionAmount(BaseModel):
    amount: Decimal
    currency: str

    @validator("amount", pre=True)
    def string_to_decimal(cls, value):
        return Decimal(value)


class Payment(BaseModel):
    transaction_id: str | None = Field(None, alias="transactionId")
    entry_reference: str | None = Field(None, alias="entryReference")
    end_to_end_id: str | None = Field(None, alias="endToEndId")
    booking_date: datetime | None = Field(None, alias="bookingDate")
    transaction_amount: PaymentTransactionAmount = Field(..., alias="transactionAmount")
    creditor_name: str | None = Field(None, alias="creditorName")
    creditor_account: PaymentAccountInfo | None
    debtor_name: str | None = Field(None, alias="debtorName")
    debtor_account: PaymentAccountInfo | None
    remittance_information_unstructured: str | None = Field(
        None, alias="remittanceInformationUnstructured"
    )
    remittance_information_structured: str | None = Field(
        None, alias="remittanceInformationStructured"
    )
    type: Literal[PaymentType.GOCARDLESS] = Field(default=PaymentType.GOCARDLESS.value)

    class Config:
        allow_population_by_field_name = True

    @validator("booking_date", pre=True)
    def parse_datetime(cls, value):
        return datetime.fromisoformat(value) if value is not None else None

    @property
    def route(self):
        if self.transaction_amount.amount > 0:
            return Route.INCOME
        else:
            return Route.EXPENSES

    def get_creditor_account(self):
        if self.creditor_account is not None:
            return self.creditor_account.iban
        else:
            return None

    def get_debtor_account(self):
        if self.debtor_account is not None:
            return self.debtor_account.iban
        else:
            return None

    def to_dict(self):
        d = self.dict()
        del d["creditor_account"]
        del d["debtor_account"]
        del d["transaction_amount"]
        d["creditor_account"] = self.get_creditor_account()
        d["debtor_account"] = self.get_debtor_account()
        d["transaction_amount"] = self.transaction_amount.amount
        d["route"] = self.route
        return d


class AccountMetadata(BaseModel):
    id: str | None
    created: datetime | None
    last_accessed: datetime | None
    iban: str | None
    institution_id: str | None
    status: str | None
    owner_name: str | None


class AccountDetailsAccount(BaseModel):
    name: str | None


class AccountDetails(BaseModel):
    account: AccountDetailsAccount | None

    def get_name(self):
        if self.account is None:
            return None
        else:
            return self.account.name
