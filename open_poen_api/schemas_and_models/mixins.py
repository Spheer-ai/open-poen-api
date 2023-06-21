from sqlmodel import Field, Column
from datetime import datetime
from pydantic import BaseModel, ConstrainedDecimal
from sqlalchemy import Column, DateTime


class TimeStampMixin(BaseModel):
    created_at: datetime | None = Field(
        sa_column=Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False,
        )
    )

    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
        )
    )


class HiddenMixin(BaseModel):
    hidden: bool | None = Field(nullable=False, default=False)


class NotNullValidatorMixin:
    """This validator helps enforce the condition that certain fields cannot be set to `None`. This is useful
    in situations where you want to distinguish between a field being omitted from a request (which is allowed)
    and a field being explicitly set to `None` (which is not allowed)."""

    @staticmethod
    def not_null(value, field):
        if value is None:
            raise ValueError(f"{field.name} cannot be null")
        return value


class Money(ConstrainedDecimal):
    """This amount can be at the most one billion and can't have more than two decimal places."""

    max_digits = 10
    decimal_places = 2
