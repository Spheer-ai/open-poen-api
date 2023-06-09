from pydantic import BaseModel, Extra, validator
from .mixins import TimeStampMixin, HiddenMixin, NotNullValidatorMixin
from .models.entities import ActivityBase


class ActivityCreateInitiativeOwner(ActivityBase):
    activity_owner_ids: list[int] | None

    class Config:
        title = "ActivityCreate"
        extra = Extra.forbid


class ActivityUpdateInitiativeOwner(HiddenMixin, NotNullValidatorMixin):
    name: str | None
    description: str | None
    purpose: str | None
    target_audience: str | None
    image: str | None
    # NOTE: Purposefully leaving out fields related to finishing.
    # I'll probably make a separate endpoint for this.
    activity_owner_ids: list[int] | None

    class Config:
        title = "ActivityUpdate"
        extra = Extra.forbid

    @validator("name", "description", "purpose", "target_audience", "image", "hidden")
    def val_fields(cls, value, field):
        return cls.not_null(value, field)


class ActivityOutputGuest(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    image: str | None
    finished_description: str | None
    finished: bool


class ActivityOutputUser(ActivityOutputGuest):
    pass


class ActivityOutputUserOwner(ActivityOutputUser):
    pass


class ActivityOutputActivityOwner(ActivityOutputUserOwner):
    pass


class ActivityOutputInitiativeOwner(ActivityOutputActivityOwner, HiddenMixin):
    pass


class ActivityOutputAdmin(ActivityOutputInitiativeOwner, TimeStampMixin):
    pass

    class Config:
        title = "ActivityOutput"


class ActivityOutputGuestList(BaseModel):
    activities: list[ActivityOutputGuest]

    class Config:
        orm_mode = True


class ActivityOutputInitiativeOwnerList(BaseModel):
    activities: list[ActivityOutputInitiativeOwner]

    class Config:
        orm_mode = True


class ActivityOutputAdminList(BaseModel):
    activities: list[ActivityOutputAdmin]

    class Config:
        title = "ActivityOutputList"
        orm_mode = True
