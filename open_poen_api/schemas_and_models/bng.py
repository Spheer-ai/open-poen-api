from .models.entities import BNGBase
from pydantic import BaseModel
from datetime import datetime
from .mixins import TimeStampMixin


class BNGCreateAdmin(BNGBase):
    pass


class BNGOutputUser(BaseModel):
    id: int
    expires_on: datetime
    last_import_on: datetime | None


class BNGOutputAdmin(BNGOutputUser, TimeStampMixin):
    iban: str
