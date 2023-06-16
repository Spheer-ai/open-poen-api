from sqlmodel import SQLModel, Field, Column, VARCHAR, Relationship, UniqueConstraint
from datetime import datetime
from pydantic import EmailStr, BaseModel
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
    hidden: bool = Field(nullable=False, default=False)


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


class UserBase(SQLModel, HiddenMixin):
    email: EmailStr = Field(sa_column=Column("email", VARCHAR, unique=True, index=True))
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


class User(UserBase, TimeStampMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    initiatives: list["Initiative"] = Relationship(
        back_populates="initiative_owners", link_model=InitiativeToUser
    )
    activities: list["Activity"] = Relationship(
        back_populates="activity_owners", link_model=ActivityToUser
    )


class UserIn(UserBase):
    initiative_ids: list[int] | None
    activity_ids: list[int] | None


class UserOut(UserBase, TimeStampMixin):
    id: int


class UserOutList(BaseModel):
    users: list[UserOut]


# INITIATIVE
class InitiativeBase(SQLModel, HiddenMixin):
    name: str = Field(index=True, unique=True)
    description: str
    purpose: str
    target_audience: str
    owner: str
    owner_email: EmailStr = Field(sa_column=Column("email", VARCHAR))
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


class InitiativeIn(InitiativeBase):
    initiative_owner_ids: list[int] | None
    activity_ids: list[int] | None


class InitiativeOut(InitiativeBase, TimeStampMixin):
    id: int


class InitiativeOutList(BaseModel):
    initiatives: list[InitiativeOut]


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


class ActivityIn(ActivityBase):
    activity_owner_ids: list[int] | None


class ActivityOut(ActivityBase, TimeStampMixin):
    id: int


class ActivityOutList(BaseModel):
    activities: list[ActivityOut]


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
class InitiativeOutWithLinkedEntities(InitiativeOut):
    initiative_owners: list[UserOut]
    activities: list[ActivityOut]


class UserOutWithLinkedEntities(UserOut):
    initiatives: list[InitiativeOut]
    activities: list[ActivityOut]


class ActivityOutWithLinkedEntities(ActivityOut):
    activity_owners: list[UserOut]
    initiative: InitiativeOut
