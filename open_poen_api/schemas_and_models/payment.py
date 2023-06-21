from pydantic import BaseModel, Extra, validator
from .mixins import TimeStampMixin, Money
from .models.entities import PaymentBase, Route, PaymentType
from .mixins import NotNullValidatorMixin, HiddenMixin
from datetime import datetime


class PaymentCreateFinancial(PaymentBase):
    pass

    class Config:
        title = "PaymentCreate"
        extra = Extra.forbid


class PaymentUpdateActivityOwner(BaseModel, NotNullValidatorMixin):
    short_user_description: str | None
    long_user_description: str | None

    @validator("short_user_description", "long_user_description")
    def val_descriptions(cls, value, field):
        return cls.not_null(value, field)


class PaymentUpdateInitiativeOwner(PaymentUpdateActivityOwner, HiddenMixin):
    route: Route | None

    @validator("route", "hidden")
    def val_route_and_hidden(cls, value, field):
        return cls.not_null(value, field)


class PaymentUpdateFinancial(PaymentUpdateInitiativeOwner):
    booking_date: datetime | None
    transaction_amount: Money | None
    creditor_name: str | None
    creditor_account: str | None
    debtor_name: str | None
    debtor_account: str | None

    @validator(
        "booking_date",
        "transaction_amount",
        "creditor_name",
        "creditor_account",
        "debtor_name",
        "debtor_account",
    )
    def val_fields(cls, value, field):
        return cls.not_null(value, field)


class PaymentOutputGuest(BaseModel):
    id: int
    booking_date: datetime
    transaction_amount: Money
    creditor_name: str
    creditor_account: str
    debtor_name: str
    debtor_account: str
    route: Route
    short_user_description: str | None
    long_user_description: str | None
    remittance_information_unstructured: str | None
    remittance_information_structured: str | None
    type: PaymentType


class PaymentOutputAdmin(PaymentOutputGuest, TimeStampMixin, HiddenMixin):
    pass

    class Config:
        title = "PaymentOutput"


class PaymentOutputGuestList(BaseModel):
    payments: list[PaymentOutputGuest]

    class Config:
        orm_mode = True


class PaymentOutputAdminList(BaseModel):
    payments: list[PaymentOutputAdmin]

    class Config:
        orm_mode = True
