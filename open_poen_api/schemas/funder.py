from pydantic import BaseModel, HttpUrl, Field
from .mixins import NotNullValidatorMixin


class FunderRead(BaseModel):
    id: int
    name: str
    url: str

    class Config:
        orm_mode = True


class FunderReadList(BaseModel):
    funders: list[FunderRead]

    class Config:
        orm_mode = True


class FunderCreate(BaseModel):
    name: str = Field(max_length=128)
    url: HttpUrl


class FunderUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = ["name", "url"]

    name: str | None = Field(max_length=128)
    url: HttpUrl | None
