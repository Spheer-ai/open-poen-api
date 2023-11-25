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
    name: str = Field(max_length=64)
    description: str = Field(max_length=512)
    purpose: str = Field(max_length=64)
    target_audience: str = Field(max_length=64)
    owner: str = Field(max_length=64)
    owner_email: str = Field(max_length=320)
    legal_entity: LegalEntity
    address_applicant: str = Field(max_length=256)
    kvk_registration: str = Field(max_length=16)
    location: str = Field(max_length=64)
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

    name: str | None = Field(max_length=64)
    description: str | None = Field(max_length=512)
    purpose: str | None = Field(max_length=64)
    target_audience: str | None = Field(max_length=64)
    owner: str | None = Field(max_length=64)
    owner_email: str | None = Field(max_length=320)
    legal_entity: LegalEntity | None
    address_applicant: str | None = Field(max_length=256)
    kvk_registration: str | None = Field(max_length=16)
    location: str | None = Field(max_length=64)
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
