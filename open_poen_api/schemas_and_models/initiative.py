from pydantic import EmailStr, BaseModel, Extra, validator
from .mixins import TimeStampMixin, HiddenMixin, NotNullValidatorMixin
from .models.entities import InitiativeBase


class InitiativeCreateAdmin(InitiativeBase):
    initiative_owner_ids: list[int] | None
    # TODO: Remove this.
    activity_ids: list[int] | None

    class Config:
        title = "InitiativeCreate"
        extra = Extra.forbid


class InitiativeUpdateInitiativeOwner(BaseModel, NotNullValidatorMixin):
    description: str | None

    class Config:
        extra = Extra.forbid
        orm_mode = True

    @validator("description")
    def val_description(cls, value, field):
        return cls.not_null(value, field)


class InitiativeUpdateAdmin(InitiativeUpdateInitiativeOwner, HiddenMixin):
    name: str | None
    purpose: str | None
    target_audience: str | None
    owner: str | None
    owner_email: EmailStr | None
    address_applicant: str | None
    kvk_registration: str | None
    location: str | None
    hidden_sponsors: bool | None
    initiative_owner_ids: list[int] | None
    # TODO: Remove this.
    activity_ids: list[int] | None

    class Config:
        title = "InitiativeUpdate"
        extra = Extra.forbid

    @validator(
        "name",
        "purpose",
        "target_audience",
        "owner",
        "owner_email",
        "address_applicant",
        "kvk_registration",
        "location",
        "hidden_sponsors",
        "hidden",
    )
    def val_fields(cls, value, field):
        return cls.not_null(value, field)


class InitiativeOutputGuest(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    kvk_registration: str
    location: str


class InitiativeOutputUser(InitiativeOutputGuest):
    pass


class InitiativeOutputUserOwner(InitiativeOutputUser):
    pass


class InitiativeOutputActivityOwner(InitiativeOutputUserOwner):
    owner: str | None
    owner_email: str | None
    address_applicant: str | None
    hidden_sponsors: bool | None


class InitiativeOutputInitiativeOwner(InitiativeOutputActivityOwner):
    pass


class InitiativeOutputAdmin(
    InitiativeOutputInitiativeOwner, TimeStampMixin, HiddenMixin
):
    pass

    class Config:
        title = "InitiativeOutput"


class InitiativeOutputGuestList(BaseModel):
    initiatives: list[InitiativeOutputGuest]

    class Config:
        orm_mode = True


class InitiativeOutputActivityOwnerList(BaseModel):
    initiatives: list[InitiativeOutputActivityOwner]

    class Config:
        orm_mode = True


class InitiativeOutputAdminList(BaseModel):
    initiatives: list[InitiativeOutputAdmin]

    class Config:
        title = "InitiativeOutputList"
        orm_mode = True
