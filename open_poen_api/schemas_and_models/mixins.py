from fastapi import Query, HTTPException
import re
from pydantic import validator


def validate_iban(iban: str = Query(...)):
    # Roughly validate an IBAN: begins with two uppercase letters followed by 2 digits and up to 30 alphanumeric characters
    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$", iban):
        raise HTTPException(status_code=400, detail="Invalid IBAN format")
    return iban


# class TimeStampMixin(BaseModel):
#     created_at: datetime | None = Field(
#         sa_column=Column(
#             DateTime,
#             default=datetime.utcnow,
#             nullable=False,
#         )
#     )

#     updated_at: datetime | None = Field(
#         sa_column=Column(
#             DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
#         )
#     )


# class HiddenMixin(BaseModel):
#     hidden: bool | None = Field(nullable=False, default=False)


# class NotNullValidatorMixin:
#     """This validator helps enforce the condition that certain fields cannot be set to `None`. This is useful
#     in situations where you want to distinguish between a field being omitted from a request (which is allowed)
#     and a field being explicitly set to `None` (which is not allowed)."""

#     @staticmethod
#     def not_null(value, field):
#         if value is None:
#             raise ValueError(f"{field.name} cannot be null")
#         return value


class NotNullValidatorMetaclass(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        for field_name in cls.NOT_NULL_FIELDS:
            cls.add_not_null_validator(field_name)

    def add_not_null_validator(cls, field_name):
        def validator_func(cls, value):
            if value is None:
                raise ValueError(f"{field_name} cannot be null")
            return value

        validator_func.__name__ = f"validate_{field_name}_not_null"
        setattr(
            cls,
            validator_func.__name__,
            classmethod(validator(field_name)(validator_func)),
        )


class NotNullValidatorMixin(metaclass=NotNullValidatorMetaclass):
    NOT_NULL_FIELDS = []


# class Money(ConstrainedDecimal):
#     """This amount can be at the most one billion and can't have more than two decimal places."""

#     max_digits = 10
#     decimal_places = 2
