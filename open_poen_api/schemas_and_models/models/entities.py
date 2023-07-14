from pydantic import EmailStr
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    String,
    VARCHAR,
    Boolean,
    Table,
)
from datetime import datetime
from enum import Enum
from sqlalchemy_utils import ChoiceType

# from ..mixins import TimeStampMixin, HiddenMixin, Money
from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from fastapi_users.db import SQLAlchemyBaseUserTable


class Base(DeclarativeBase):
    pass


user_initiative = Table(
    "user_initiative",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("initiative_id", Integer, ForeignKey("initiative.id")),
)


class Role(str, Enum):
    """These are the roles we save in the db, but there are more roles that
    are not based on a a field, but on relationship(s)."""

    FINANCIAL = "financial"
    ADMINISTRATOR = "administrator"
    USER = "user"


class User(SQLAlchemyBaseUserTable[int], Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(length=64))
    last_name: Mapped[str | None] = mapped_column(String(length=64))
    biography: Mapped[str | None] = mapped_column(String(length=512))
    role: Mapped[Role] = mapped_column(ChoiceType(Role, impl=VARCHAR(length=32)))
    image: Mapped[str | None] = mapped_column(String(length=128))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    bng = relationship("BNG", uselist=False, back_populates="user")
    initiatives = relationship(
        "Initiative",
        secondary=user_initiative,
        back_populates="initiative_owners",
    )

    def __repr__(self):
        return f"User(id={self.id}, name='{self.first_name} {self.last_name}', role='{self.role}', is_superuser='{self.is_superuser}')"


class BNG(Base):
    __tablename__ = "bng"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    iban: Mapped[str] = mapped_column(String(length=64), nullable=False)
    expires_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_id: Mapped[str] = mapped_column(String(length=64))
    access_token: Mapped[str] = mapped_column(String(length=2048))
    last_import_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="bng")

    def __repr__(self):
        return f"BNG(id={self.id}, iban='{self.iban}', expires_on='{self.expires_on}'"


class LegalEntity(str, Enum):
    STICHTING = "stichting"
    VERENIGING = "vereniging"
    EENMANSZAAK = "eenmanszaak"
    VOF = "vennootschap onder firma"
    MAATSCHAP = "maatschap"
    BV = "besloten vennootschap"
    COOPERATIE = "coöperatie"
    GEEN = "geen (natuurlijk persoon)"


class Initiative(Base):
    __tablename__ = "initiative"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=64), nullable=False)
    description: Mapped[str] = mapped_column(String(length=512), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(length=64), nullable=False)
    owner: Mapped[str] = mapped_column(String(length=64), nullable=False)
    owner_email: Mapped[str] = mapped_column(String(length=320), nullable=False)
    legal_entity: Mapped[LegalEntity] = mapped_column(
        ChoiceType(LegalEntity, impl=VARCHAR(length=32))
    )
    address_applicant: Mapped[str] = mapped_column(String(length=256), nullable=False)
    kvk_registration: Mapped[str | None] = mapped_column(String(length=16))
    location: Mapped[str] = mapped_column(String(length=64), nullable=False)
    image: Mapped[str | None] = mapped_column(String(length=128))
    hidden_sponsors: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    initiative_owners = relationship(
        "User",
        secondary=user_initiative,
        back_populates="initiatives",
    )

    def __repr__(self):
        return f"Initiative(id={self.id}, name='{self.name}'"


# class UserBase(SQLModel, HiddenMixin):
#     email: EmailStr = Field(
#         sa_column=Column("email", VARCHAR, unique=True, index=True, nullable=False)
#     )
#     first_name: str | None
#     last_name: str | None
#     biography: str | None
#     role: Role = Field(
#         sa_column=Column(ChoiceType(Role, impl=VARCHAR(length=32))),
#         nullable=False,
#         default=Role.USER,
#     )
#     active: bool = Field(nullable=False, default=True)
#     image: str | None


# class User(UserBase, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     hashed_password: str
#     initiatives: list["Initiative"] = Relationship(
#         back_populates="initiative_owners", link_model=InitiativeToUser
#     )
#     activities: list["Activity"] = Relationship(
#         back_populates="activity_owners", link_model=ActivityToUser
#     )
#     bng: Optional["BNG"] = Relationship(back_populates="user")
#     requisitions: list["Requisition"] = Relationship(back_populates="user")


# class InitiativeBase(SQLModel, HiddenMixin):
#     name: str = Field(index=True, unique=True)
#     description: str
#     purpose: str
#     target_audience: str
#     owner: str
#     owner_email: EmailStr = Field(sa_column=Column("email", VARCHAR, nullable=False))
#     # legal_entity
#     address_applicant: str
#     kvk_registration: str
#     location: str
#     # budget
#     # files
#     image: str | None
#     hidden_sponsors = Field(nullable=False, default=False)


# class Initiative(InitiativeBase, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     initiative_owners: list["User"] = Relationship(
#         back_populates="initiatives", link_model=InitiativeToUser
#     )
#     activities: list["Activity"] = Relationship(
#         back_populates="initiative",
#         sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
#     )
#     payments: list["Payment"] = Relationship(back_populates="initiative")
#     debit_cards: list["DebitCard"] = Relationship(back_populates="initiative")


# class ActivityBase(SQLModel, HiddenMixin):
#     name: str
#     description: str
#     purpose: str
#     target_audience: str
#     image: str | None
#     # budget
#     finished_description: str | None
#     finished: bool = Field(nullable=False, default=False)


# class Activity(ActivityBase, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     activity_owners: list["User"] = Relationship(
#         back_populates="activities", link_model=ActivityToUser
#     )
#     initiative_id: int = Field(
#         sa_column=Column(
#             Integer, ForeignKey("initiative.id", ondelete="CASCADE"), nullable=False
#         )
#     )
#     initiative: "Initiative" = Relationship(back_populates="activities")
#     payments: list["Payment"] = Relationship(back_populates="activity")

#     __table_args__ = (
#         UniqueConstraint("name", "initiative_id", name="unique_activity_name"),
#     )


# class Route(str, Enum):
#     """We need to distinguish between incoming and outcoming funds, so that
#     we can take corrective payments into account in the calculation rules, such
#     as refunds."""

#     INCOME = "income"
#     EXPENSES = "expenses"


# class PaymentType(str, Enum):
#     BNG = "BNG"
#     NORDIGEN = "NORDIGEN"
#     MANUAL = "MANUAL"


# class PaymentBase(SQLModel, HiddenMixin):
#     booking_date: datetime = Field(sa_column=Column(DateTime(timezone=True)))
#     transaction_amount: Money
#     creditor_name: str
#     creditor_account: str
#     debtor_name: str
#     debtor_account: str
#     route: Route = Field(
#         sa_column=Column(ChoiceType(Route, impl=VARCHAR(length=32))),
#         nullable=False,
#     )
#     short_user_description: str | None
#     long_user_description: str | None


# class Payment(PaymentBase, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     transaction_id: str | None
#     entry_reference: str | None
#     end_to_end_id: str | None
#     remittance_information_unstructured: str | None
#     remittance_information_structured: str | None
#     type: PaymentType = Field(
#         sa_column=Column(
#             ChoiceType(PaymentType, impl=VARCHAR(length=32)), default=PaymentType.MANUAL
#         ),
#         nullable=False,
#     )
#     # TODO: How should these cascades work?
#     initiative_id: int = Field(
#         sa_column=Column(Integer, ForeignKey("initiative.id", ondelete="CASCADE"))
#     )
#     initiative: Initiative = Relationship(back_populates="payments")
#     # TODO: How should these cascades work?
#     activity_id: int = Field(
#         sa_column=Column(Integer, ForeignKey("activity.id", ondelete="CASCADE"))
#     )
#     activity: Activity = Relationship(back_populates="payments")
#     debit_card_id: int | None = Field(
#         sa_column=Column(Integer, ForeignKey("debitcard.id"), nullable=True)
#     )
#     debit_card: "DebitCard" = Relationship(back_populates="payments")


# class DebitCardBase(SQLModel):
#     card_number: str = Field(unique=True, nullable=False)


# class DebitCard(DebitCardBase, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     initiative_id: int | None = Field(
#         sa_column=Column(Integer, ForeignKey("initiative.id"), nullable=True)
#     )
#     initiative: Initiative = Relationship(back_populates="debit_cards")
#     payments: list[Payment] = Relationship(back_populates="debit_card")


# class Requisition(SQLModel, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     user_id: int = Field(
#         sa_column=Column(Integer, ForeignKey("user.id"), nullable=False)
#     )
#     user: User = Relationship(back_populates="requisitions")
#     api_institution_id: str
#     api_requisition_id: str

#     __table_args__ = (
#         UniqueConstraint("api_institution_id", "user_id", name="single_bank_per_user"),
#     )


# class Account(SQLModel, TimeStampMixin, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     api_account_id: str

#     requisition_id: int | None = Field(
#         sa_column=Column(Integer, ForeignKey("requisition.id"), nullable=True)
#     )
#     requisition: Requisition = Relationship(back_populates="accounts")

#     initiative_id: int | None = Field(
#         sa_column=Column(Integer, ForeignKey("initiative.id"), nullable=True)
#     )
#     initiative: Initiative = Relationship(back_populates="accounts")
