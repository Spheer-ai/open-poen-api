from pydantic import BaseModel, validator
from datetime import datetime


class BankAccountRead(BaseModel):
    id: int
    iban: str
    name: str
    created: datetime
    last_accessed: datetime
    linked_requisitions: int


class BankAccountUsersUpdate(BaseModel):
    user_ids: list[int]

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))
