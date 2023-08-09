from pydantic import BaseModel, validator
from .mixins import NotNullValidatorMixin
from ..models import RegulationRole


class RegulationRead(BaseModel):
    id: int
    name: str
    description: str

    class Config:
        orm_mode = True


class RegulationReadList(BaseModel):
    regulations: list[RegulationRead]

    class Config:
        orm_mode = True


class RegulationCreate(BaseModel):
    name: str
    description: str


class RegulationOfficersUpdate(BaseModel):
    user_ids: list[int]
    role: RegulationRole

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))


class RegulationUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS = ["name", "description"]

    name: str | None
    description: str | None
