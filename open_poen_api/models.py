from sqlmodel import SQLModel, Field, Column, VARCHAR, Relationship, UniqueConstraint
from datetime import datetime
from pydantic import EmailStr, BaseModel, Extra, validator
from enum import Enum
from sqlalchemy_utils import ChoiceType
from sqlalchemy import Column, Integer, ForeignKey, DateTime


# MIXINS
class TimeStampMixin(BaseModel):
    created_at: datetime | None = Field(
        sa_column=Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False,
        )
    )

    updated_at: datetime | None = Field(
        sa_column=Column(
            DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
        )
    )


class HiddenMixin(BaseModel):
    hidden: bool | None = Field(nullable=False, default=False)


class NotNullValidatorMixin:
    """This validator helps enforce the condition that certain fields cannot be set to `None`. This is useful
    in situations where you want to distinguish between a field being omitted from a request (which is allowed)
    and a field being explicitly set to `None` (which is not allowed)."""

    @staticmethod
    def not_null(value, field):
        if value is None:
            raise ValueError(f"{field.name} cannot be null")
        return value


# LINK MODELS
class InitiativeToUser(SQLModel, table=True):
    initiative_id: int | None = Field(
        default=None, foreign_key="initiative.id", primary_key=True
    )
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)


class ActivityToUser(SQLModel, table=True):
    activity_id: int | None = Field(
        default=None, foreign_key="activity.id", primary_key=True
    )
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)


# USER
class Role(str, Enum):
    """These are the roles we save in the db, but there are more roles that
    are not based on a a field, but on relationship(s)."""

    ADMIN = "admin"
    FINANCIAL = "financial"
    USER = "user"


class UserInputBase(SQLModel, HiddenMixin):
    email: EmailStr = Field(
        sa_column=Column("email", VARCHAR, unique=True, index=True, nullable=False)
    )
    first_name: str | None
    last_name: str | None
    biography: str | None
    role: Role = Field(
        sa_column=Column(ChoiceType(Role, impl=VARCHAR(length=32))),
        nullable=False,
        default=Role.USER,
    )
    active: bool = Field(nullable=False, default=True)
    image: str | None


class User(UserInputBase, TimeStampMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    initiatives: list["Initiative"] = Relationship(
        back_populates="initiative_owners", link_model=InitiativeToUser
    )
    activities: list["Activity"] = Relationship(
        back_populates="activity_owners", link_model=ActivityToUser
    )


class UserCreateAdmin(UserInputBase):
    initiative_ids: list[int] | None
    activity_ids: list[int] | None

    class Config:
        title = "UserCreate"
        extra = Extra.forbid


class UserUpdateUserOwner(BaseModel, NotNullValidatorMixin):
    email: EmailStr | None
    first_name: str | None
    last_name: str | None
    biography: str | None

    class Config:
        extra = Extra.forbid
        orm_mode = True

    @validator("email")
    def val_email(cls, value, field):
        return cls.not_null(value, field)


class UserUpdateAdmin(UserUpdateUserOwner, HiddenMixin):
    role: Role | None
    active: bool | None
    initiative_ids: list[int] | None
    activity_ids: list[int] | None

    class Config:
        title = "UserUpdate"
        extra = Extra.forbid

    @validator("role", "active")
    def val_role_active(cls, value, field):
        return cls.not_null(value, field)


class UserOutputGuest(BaseModel):
    id: int
    first_name: str | None
    biography: str | None
    role: Role
    image: str | None


class UserOutputUser(UserOutputGuest):
    last_name: str | None


class UserOutputUserOwner(UserOutputUser):
    pass


class UserOutputActivityOwner(UserOutputUserOwner):
    pass


class UserOutputAdmin(UserOutputActivityOwner, TimeStampMixin, HiddenMixin):
    email: EmailStr | None
    active: bool | None

    class Config:
        title = "UserOutput"


class UserOutputUserList(BaseModel):
    users: list[UserOutputUser]

    class Config:
        orm_mode = True


class UserOutputUserOwnerList(BaseModel):
    users: list[UserOutputUserOwner]

    class Config:
        orm_mode = True


class UserOutputAdminList(BaseModel):
    users: list[UserOutputAdmin]

    class Config:
        title = "UserOutputList"
        orm_mode = True


# INITIATIVE
class InitiativeBase(SQLModel, HiddenMixin):
    name: str = Field(index=True, unique=True)
    description: str
    purpose: str
    target_audience: str
    owner: str
    owner_email: EmailStr = Field(sa_column=Column("email", VARCHAR, nullable=False))
    # legal_entity
    address_applicant: str
    kvk_registration: str
    location: str
    # budget
    # files
    image: str | None
    hidden_sponsors = Field(nullable=False, default=False)


class Initiative(InitiativeBase, TimeStampMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    initiative_owners: list[User] = Relationship(
        back_populates="initiatives", link_model=InitiativeToUser
    )
    activities: list["Activity"] = Relationship(
        back_populates="initiative",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    payments: list["Payment"] = Relationship(back_populates="initiative")


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
    owner: str
    owner_email: str
    address_applicant: str
    hidden_sponsors: bool


class InitiativeOutputAdmin(InitiativeOutputActivityOwner, TimeStampMixin, HiddenMixin):
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
        title = "InitiativeOutputList"
        orm_mode = True


# ACTIVITY
class ActivityBase(SQLModel, HiddenMixin):
    name: str
    description: str
    purpose: str
    target_audience: str
    image: str | None
    # budget
    finished_description: str | None
    finished: bool = Field(nullable=False, default=False)


class Activity(ActivityBase, TimeStampMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    activity_owners: list[User] = Relationship(
        back_populates="activities", link_model=ActivityToUser
    )
    initiative_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("initiative.id", ondelete="CASCADE"), nullable=False
        )
    )
    initiative: Initiative = Relationship(back_populates="activities")
    payments: list["Payment"] = Relationship(back_populates="activity")

    __table_args__ = (
        UniqueConstraint("name", "initiative_id", name="unique_activity_name"),
    )


class ActivityCreateAdmin(ActivityBase):
    activity_owner_ids: list[int] | None

    class Config:
        title = "ActivityCreate"
        extra = Extra.forbid


class ActivityUpdateActivtyOwner(BaseModel, NotNullValidatorMixin):
    name: str | None
    description: str | None
    purpose: str | None
    target_audience: str | None
    image: str | None
    # NOTE: Purposefully leaving out fields related to finishing.
    # I'll probably make a separate endpoint for this.

    class Config:
        title = "ActivityUpdate"
        extra = Extra.forbid

    @validator("name", "descriptioen", "purpose", "target_audience", "image")
    def val_fields(cls, value, field):
        return cls.not_null(value, field)


class ActivityOutputGuest(BaseModel):
    id: int
    name: str
    description: str
    purpose: str
    target_audience: str
    image: str
    finished_description: str | None
    finished: bool


class ActivityOutputUser(ActivityOutputGuest):
    pass


class ActivityOutputUserOwner(ActivityOutputUser):
    pass


class ActivityOutputActivityOwner(ActivityOutputUserOwner):
    pass


class ActivityOutputAdmin(ActivityOutputActivityOwner, HiddenMixin, TimeStampMixin):
    pass

    class Config:
        title = "ActivityOutput"


class ActivityOutputGuestList(BaseModel):
    activities: list[ActivityOutputGuest]

    class Config:
        orm_mode = True


class ActivityOutputAdminList(BaseModel):
    activities: list[ActivityOutputAdmin]

    class Config:
        title = "ActivityOutputList"
        orm_mode = True


# PAYMENT
class Route(str, Enum):
    """We need to distinguish between incoming and outcoming funds, so that
    we can take corrective payments into account in the calculation rules, such
    as refunds."""

    INCOME = "income"
    EXPENSES = "expenses"


def get_default_route(context):
    ta = context.get_current_parameters()["transaction_amount"]
    return Route.INCOME if ta > 0 else Route.EXPENSES


class PaymentType(str, Enum):
    BNG = "BNG"
    NORDIGEN = "NORDIGEN"
    MANUAL = "MANUAL"


class PaymentBase(SQLModel, TimeStampMixin, HiddenMixin):
    transaction_id: str | None
    entry_reference: str | None
    end_to_end_id: str | None
    booking_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    # transaction_amount (Add rule on amount != 0)
    creditor_name: str | None
    creditor_account: str | None
    debtor_name: str | None
    debtor_account: str | None
    remittance_information_unstructured: str | None
    remittance_information_structured: str | None
    type: PaymentType = Field(
        sa_column=Column(ChoiceType(PaymentType, impl=VARCHAR(length=32))),
        nullable=False,
    )
    route: Route = Field(
        sa_column=Column(ChoiceType(Route, impl=VARCHAR(length=32))),
        nullable=False,
        default=get_default_route,
    )
    # debit_card_id: int | None
    short_user_description: str | None
    long_user_description: str | None


class Payment(PaymentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # TODO: How should these cascades work?
    initiative_id: int = Field(
        sa_column=Column(Integer, ForeignKey("initiative.id", ondelete="CASCADE"))
    )
    initiative: Initiative = Relationship(back_populates="payments")
    # TODO: How should these cascades work?
    activity_id: int = Field(
        sa_column=Column(Integer, ForeignKey("activity.id", ondelete="CASCADE"))
    )
    activity: Activity = Relationship(back_populates="payments")


class PaymentIn(PaymentBase):
    pass


class PaymentOut(PaymentBase, TimeStampMixin):
    id: int


class PaymentOutList(BaseModel):
    payments: list[PaymentOut]


# OUTPUT MODELS WITH LINKED ENTITIES
class InitiativeOutputGuestWithLinkedEntities(InitiativeOutputGuest):
    initiative_owners: list[UserOutputGuest]
    activities: list[ActivityOutputGuest]


class InitiativeOutputActivityOwnerWithLinkedEntities(InitiativeOutputActivityOwner):
    initiative_owners: list[UserOutputActivityOwner]
    activities: list[ActivityOutputActivityOwner]

    class Config:
        orm_mode = True
        title = "InitiativeOutputWithLinkedEntities"


class UserOutputUserWithLinkedEntities(UserOutputUser):
    initiatives: list[InitiativeOutputUser]
    activities: list[ActivityOutputUser]

    class Config:
        orm_mode = True


class UserOutputUserOwnerWithLinkedEntities(UserOutputUserOwner):
    initiatives: list[InitiativeOutputUserOwner]
    activities: list[ActivityOutputUserOwner]

    class Config:
        orm_mode = True


class UserOutputAdminWithLinkedEntities(UserOutputAdmin):
    initiatives: list[InitiativeOutputAdmin]
    activities: list[ActivityOutputAdmin]

    class Config:
        orm_mode = True
        title = "UserOutputWithLinkedEntities"


class ActivityOutputGuestWithLinkedEntities(ActivityOutputGuest):
    activity_owners: list[UserOutputGuest]
    initiative: InitiativeOutputGuest


# AUTHORIZATON
class Token(BaseModel):
    access_token: str
    token_type: str
