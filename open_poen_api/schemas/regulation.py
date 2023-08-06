from pydantic import BaseModel, HttpUrl
from .mixins import NotNullValidatorMixin


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


class RegulationUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS = ["name", "description"]

    name: str | None
    description: str | None
