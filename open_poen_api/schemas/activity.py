from pydantic import BaseModel, Field, validator
from .mixins import NotNullValidatorMixin, Budget


class ActivityRead(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    hidden: bool | None
    budget: Budget
    finished: bool
    finished_description: str | None

    class Config:
        orm_mode = True


class ActivityReadList(BaseModel):
    activities: list[ActivityRead]

    class Config:
        orm_mode = True


class ActivityCreate(BaseModel):
    name: str
    description: str
    purpose: str
    target_audience: str
    hidden: bool = Field(default=False)
    budget: Budget


class ActivityUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = [
        "name",
        "description",
        "purpose",
        "target_audience",
        "hidden",
        "finished",
        "finished_description",
        "budget",
    ]

    name: str | None
    description: str | None
    purpose: str | None
    target_audience: str | None
    hidden: bool | None
    finished: bool | None
    finished_description: bool | None
    budget: Budget | None


class ActivityOwnersUpdate(BaseModel):
    user_ids: list[int]

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))
