from pydantic import BaseModel, validator, Field
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
    name: str = Field(max_length=128)
    description: str = Field(max_length=512)


class RegulationOfficersUpdate(BaseModel):
    user_ids: list[int]
    role: RegulationRole

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))


class RegulationUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = ["name", "description"]

    name: str | None = Field(max_length=128)
    description: str | None = Field(max_length=512)
