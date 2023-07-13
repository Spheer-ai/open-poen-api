from pydantic import BaseModel, validator
import re
from datetime import datetime, timedelta
import pytz

# from .mixins import TimeStampMixin


class BNGCreate(BaseModel):
    iban: str
    expires_on: datetime

    @validator("iban")
    def validate_iban(cls, v):
        # Roughly validate an IBAN: begins with two uppercase letters followed by 2 digits and up to 30 alphanumeric characters
        if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$", v):
            raise ValueError("Invalid IBAN format")
        return v

    @validator("expires_on")
    def validate_expires_on(cls, v):
        amsterdam_tz = pytz.timezone("Europe/Amsterdam")
        now = datetime.now(amsterdam_tz)
        if v < now:
            raise ValueError("expires_on should not be before today")
        elif v > (now + timedelta(days=90)):
            raise ValueError("expires_on should not be later than 90 days from now")
        return v


class BNGInitiate(BaseModel):
    url: str


# class BNGCreateAdmin(BNGBase):
#     pass


# class BNGOutputUser(BaseModel):
#     id: int
#     expires_on: datetime
#     last_import_on: datetime | None


# class BNGOutputAdmin(BNGOutputUser, TimeStampMixin):
#     iban: str
