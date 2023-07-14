from pydantic import BaseModel
from .models.entities import LegalEntity
from .mixins import NotNullValidatorMixin


class InitiativeRead(BaseModel):
    name: str
    description: str
    target_audience: str
    owner: str | None
    owner_email: str | None
    legal_entity: LegalEntity
    address_applicant: str | None
    kvk_registration: str | None
    location: str | None
    hidden_sponsors: bool | None

    class Config:
        orm_mode = True


class InitiativeReadList(BaseModel):
    initiatives: list[InitiativeRead]

    class Config:
        orm_mode = True


class InitiativeCreate(BaseModel):
    name: str
    description: str
    target_audience: str
    owner: str
    owner_email: str
    legal_entity: LegalEntity
    address_applicant: str
    kvk_registration: str
    location: str
    hidden_sponsors: bool


class InitiativeUpdate(BaseModel, NotNullValidatorMixin):
    NOT_NULL_FIELDS = [
        "name",
        "description",
        "target_audience",
        "owner",
        "owner_email",
        "legal_entity",
        "address_applicant",
        "location",
        "hidden_sponsors",
    ]

    name: str | None
    description: str | None
    target_audience: str | None
    owner: str | None
    owner_email: str | None
    legal_entity: LegalEntity | None
    address_applicant: str | None
    kvk_registration: str | None
    location: str | None
    hidden_sponsors: bool | None
