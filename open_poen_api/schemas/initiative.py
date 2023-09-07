from pydantic import BaseModel, Field, validator, ValidationError
from ..models import LegalEntity
from .mixins import NotNullValidatorMixin, Budget, TransactionAmount


class InitiativeRead(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    owner: str | None
    owner_email: str | None
    legal_entity: LegalEntity
    address_applicant: str | None
    kvk_registration: str | None
    location: str | None
    hidden_sponsors: bool | None
    hidden: bool | None
    budget: Budget
    income: TransactionAmount
    expenses: TransactionAmount

    class Config:
        orm_mode = True


class InitiativeReadList(BaseModel):
    initiatives: list[InitiativeRead]

    class Config:
        orm_mode = True


class InitiativeCreate(BaseModel):
    name: str
    description: str
    purpose: str
    target_audience: str
    owner: str
    owner_email: str
    legal_entity: LegalEntity
    address_applicant: str
    kvk_registration: str
    location: str
    hidden_sponsors: bool = Field(default=False)
    hidden: bool = Field(default=False)
    budget: Budget


class InitiativeUpdate(NotNullValidatorMixin):
    NOT_NULL_FIELDS: list[str] = [
        "name",
        "description",
        "purpose",
        "target_audience",
        "owner",
        "owner_email",
        "legal_entity",
        "address_applicant",
        "kvk_registration",
        "location",
        "hidden_sponsors",
        "hidden",
        "budget",
    ]

    name: str | None
    description: str | None
    purpose: str | None
    target_audience: str | None
    owner: str | None
    owner_email: str | None
    legal_entity: LegalEntity | None
    address_applicant: str | None
    kvk_registration: str | None
    location: str | None
    hidden_sponsors: bool | None
    hidden: bool | None
    budget: Budget | None


class InitiativeOwnersUpdate(BaseModel):
    user_ids: list[int]

    @validator("user_ids", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))


class InitiativeDebitCardsUpdate(BaseModel):
    card_numbers: list[str]
    ignore_already_linked: bool = False

    @validator("card_numbers", pre=True)
    def remove_duplicates(cls, v):
        return list(set(v))

    @validator("card_numbers", each_item=True, pre=True)
    def remove_whitespace(cls, v):
        v = str(v)
        return v.replace(" ", "")

    @validator("card_numbers", each_item=True)
    def validate_card_numbers(cls, v):
        if not v.startswith("6731924"):
            raise ValidationError(
                f"Card number {v} does not start with 6731924. All card numbers should start with this sequence."
            )
        if not len(v) == 19:
            raise ValidationError(
                f"Card number {v} is not exactly 19 digits long, but {len(v)} digits. All card numbers should be exactly 19 digits long."
            )
        return v
