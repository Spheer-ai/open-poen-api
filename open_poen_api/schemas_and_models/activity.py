from pydantic import BaseModel, Field
from .mixins import NotNullValidatorMixin


class ActivityRead(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    hidden: bool | None
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


class InitiativeUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS = [
        "name",
        "description",
        "purpose",
        "target_audience",
        "hidden",
        "finished",
        "finished_description",
    ]

    name: str | None
    description: str | None
    purpose: str | None
    target_audience: str | None
    hidden: bool | None
    finished: bool | None
    finished_description: bool | None


class ActivityOwnersUpdate(BaseModel):
    user_ids: list[int]
