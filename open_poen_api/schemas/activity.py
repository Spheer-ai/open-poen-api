from pydantic import BaseModel, Field, validator
from .mixins import NotNullValidatorMixin, Budget, TransactionAmount
from .attachment import ProfilePicture


class ActivityRead(BaseModel):
    id: int
    initiative_id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    hidden: bool | None
    budget: Budget
    finished: bool
    finished_description: str | None
    income: TransactionAmount
    expenses: TransactionAmount
    profile_picture: ProfilePicture | None

    class Config:
        orm_mode = True


class ActivityReadList(BaseModel):
    activities: list[ActivityRead]

    class Config:
        orm_mode = True


class ActivityCreate(BaseModel):
    name: str = Field(max_length=64)
    description: str = Field(max_length=512)
    purpose: str = Field(max_length=64)
    target_audience: str = Field(max_length=64)
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

    name: str | None = Field(max_length=64)
    description: str | None = Field(max_length=512)
    purpose: str | None = Field(max_length=64)
    target_audience: str | None = Field(max_length=64)
    hidden: bool | None
    finished: bool | None
    finished_description: str | None = Field(max_length=512)
    budget: Budget | None


class ActivityOwnersUpdate(BaseModel):
    user_ids: list[int]

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))
