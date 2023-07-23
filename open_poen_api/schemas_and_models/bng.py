from pydantic import BaseModel, validator
import re
from datetime import datetime, timedelta
import pytz
from fastapi import Query, HTTPException
from datetime import date

# from .mixins import TimeStampMixin


def validate_expires_on(expires_on: date = Query(...)):
    amsterdam_tz = pytz.timezone("Europe/Amsterdam")
    today = datetime.now(amsterdam_tz).date()
    if expires_on < today:
        raise HTTPException(
            status_code=400, detail="expires_on should not be before today"
        )
    elif expires_on > (today + timedelta(days=90)):
        raise HTTPException(
            status_code=400,
            detail="expires_on should not be later than 90 days from now",
        )
    return expires_on


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
