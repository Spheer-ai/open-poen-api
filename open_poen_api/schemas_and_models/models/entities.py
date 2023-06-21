from sqlmodel import SQLModel, Field, Column, Relationship, UniqueConstraint, VARCHAR
from pydantic import EmailStr
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from datetime import datetime
from enum import Enum
from sqlalchemy_utils import ChoiceType
from ..mixins import TimeStampMixin, HiddenMixin, Money
from ..models.associations import ActivityToUser, InitiativeToUser


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
    initiative_owners: list["User"] = Relationship(
        back_populates="initiatives", link_model=InitiativeToUser
    )
    activities: list["Activity"] = Relationship(
        back_populates="initiative",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )
    payments: list["Payment"] = Relationship(back_populates="initiative")


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
    activity_owners: list["User"] = Relationship(
        back_populates="activities", link_model=ActivityToUser
    )
    initiative_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("initiative.id", ondelete="CASCADE"), nullable=False
        )
    )
    initiative: "Initiative" = Relationship(back_populates="activities")
    payments: list["Payment"] = Relationship(back_populates="activity")

    __table_args__ = (
        UniqueConstraint("name", "initiative_id", name="unique_activity_name"),
    )


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


class PaymentBase(SQLModel, HiddenMixin):
    booking_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    transaction_amount: Money
    creditor_name: str
    creditor_account: str
    debtor_name: str
    debtor_account: str
    route: Route = Field(
        sa_column=Column(ChoiceType(Route, impl=VARCHAR(length=32))),
        nullable=False,
        default=get_default_route,
    )
    short_user_description: str | None
    long_user_description: str | None


class Payment(PaymentBase, TimeStampMixin, table=True):
    id: int | None = Field(default=None, primary_key=True)
    transaction_id: str | None
    entry_reference: str | None
    end_to_end_id: str | None
    remittance_information_unstructured: str | None
    remittance_information_structured: str | None
    type: PaymentType = Field(
        sa_column=Column(
            ChoiceType(PaymentType, impl=VARCHAR(length=32)), default=PaymentType.MANUAL
        ),
        nullable=False,
    )
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
    # debit_card_id: int | None
    # debit_card: DebitCard = Relationship...
