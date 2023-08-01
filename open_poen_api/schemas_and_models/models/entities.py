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
    UniqueConstraint,
    DECIMAL,
)
from datetime import datetime
from enum import Enum
from sqlalchemy_utils import ChoiceType

# from ..mixins import TimeStampMixin, HiddenMixin, Money
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    selectinload,
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.db import SQLAlchemyBaseUserTable
from decimal import Decimal
from sqlalchemy.dialects import postgresql as pg
import uuid


class Base(DeclarativeBase):
    pass


requisition_bankaccount = Table(
    "requisition_bankaccount",
    Base.metadata,
    Column("requisition_id", Integer, ForeignKey("requisition.id"), primary_key=True),
    Column("bank_account_id", Integer, ForeignKey("bank_account.id"), primary_key=True),
)


class UserInitiativeRole(Base):
    __tablename__ = "user_initiative_roles"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    initiative_id = Column(Integer, ForeignKey("initiative.id"), primary_key=True)
    user = relationship("User", back_populates="initiative_roles")
    initiative = relationship("Initiative", back_populates="user_roles")


class UserActivityRole(Base):
    __tablename__ = "user_activity_roles"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    activity_id = Column(Integer, ForeignKey("activity.id"), primary_key=True)
    user = relationship("User", back_populates="activity_roles")
    activity = relationship("Activity", back_populates="user_roles")


class UserBankAccountRole(Base):
    __tablename__ = "bank_account_roles"
    user_id = Column(Integer, ForeignKey("user.id"), primary_key=True)
    bank_account_id = Column(Integer, ForeignKey("bank_account.id"), primary_key=True)
    user = relationship("User", back_populates="bank_account_roles")
    bank_account = relationship("BankAccount", back_populates="user_roles")


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
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    bng = relationship("BNG", uselist=False, back_populates="user", lazy="noload")
    initiative_roles = relationship(
        "UserInitiativeRole",
        back_populates="user",
        lazy="noload",
    )
    initiatives = association_proxy("initiative_roles", "initiative")
    activity_roles = relationship(
        "UserActivityRole",
        back_populates="user",
        lazy="noload",
    )
    activities = association_proxy("activity_roles", "activity")
    requisitions = relationship("Requisition", back_populates="user", lazy="noload")
    bank_account_roles = relationship(
        "UserBankAccountRole", back_populates="user", lazy="noload"
    )
    bank_accounts = association_proxy("bank_account_roles", "bank_account")

    def __repr__(self):
        return f"User(id={self.id}, name='{self.first_name} {self.last_name}', role='{self.role}', is_superuser='{self.is_superuser}')"

    REL_FIELDS = [
        "bng",
        "initiative_roles",
        "initiatives",
        "activity_roles",
        "activities",
    ]


class BNG(Base):
    __tablename__ = "bng"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    iban: Mapped[str] = mapped_column(String(length=64), nullable=False)
    expires_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_id: Mapped[str] = mapped_column(String(length=64))
    access_token: Mapped[str] = mapped_column(String(length=2048))
    last_import_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="bng", lazy="noload")

    def __repr__(self):
        return f"BNG(id={self.id}, iban='{self.iban}', expires_on='{self.expires_on}')"


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
    __table_args__ = (UniqueConstraint("name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(length=512), nullable=False)
    purpose: Mapped[str] = mapped_column(String(length=64), nullable=False)
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
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user_roles = relationship(
        "UserInitiativeRole",
        back_populates="initiative",
        lazy="noload",
        cascade="delete",
    )
    initiative_owners = association_proxy("user_roles", "user")
    activities = relationship(
        "Activity", back_populates="initiative", lazy="noload", cascade="delete"
    )
    payments = relationship("Payment", back_populates="initiative", lazy="noload")
    debit_cards: Mapped[list["DebitCard"]] = relationship(
        "DebitCard", back_populates="initiative", lazy="noload"
    )

    def __repr__(self):
        return f"Initiative(id={self.id}, name='{self.name}')"


class Activity(Base):
    __tablename__ = "activity"
    __table_args__ = (UniqueConstraint("name", "initiative_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(length=64), nullable=False)
    description: Mapped[str] = mapped_column(String(length=512), nullable=False)
    purpose: Mapped[str] = mapped_column(String(length=64), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(length=64), nullable=False)
    image: Mapped[str | None] = mapped_column(String(length=128))
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finished_description: Mapped[str] = mapped_column(String(length=512), nullable=True)

    user_roles = relationship(
        "UserActivityRole",
        back_populates="activity",
        lazy="noload",
    )
    activity_owners = association_proxy("user_roles", "user")
    initiative_id: Mapped[int] = mapped_column(Integer, ForeignKey("initiative.id"))
    initiative = relationship("Initiative", back_populates="activities", lazy="noload")
    payments = relationship("Payment", back_populates="activity", lazy="noload")

    def __repr__(self):
        return f"Activity(id={self.id}, name='{self.name}')"


class Route(str, Enum):
    """We need to distinguish between incoming and outcoming funds, so that
    we can take corrective payments into account in the calculation rules, such
    as refunds."""

    INCOME = "income"
    EXPENSES = "expenses"


class PaymentType(str, Enum):
    BNG = "BNG"
    GOCARDLESS = "GOCARDLESS"
    MANUAL = "MANUAL"


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(length=64), unique=True, nullable=False, index=True
    )
    entry_reference: Mapped[str] = mapped_column(String(length=128), nullable=True)
    end_to_end_id: Mapped[str] = mapped_column(String(length=128), nullable=True)
    booking_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    transaction_amount: Mapped[Decimal] = mapped_column(DECIMAL(precision=8, scale=2))
    creditor_name: Mapped[str] = mapped_column(String(length=128), nullable=True)
    creditor_account: Mapped[str] = mapped_column(String(length=128), nullable=True)
    debtor_name: Mapped[str] = mapped_column(String(length=128), nullable=True)
    debtor_account: Mapped[str] = mapped_column(String(length=128), nullable=True)
    route: Mapped[Route] = mapped_column(ChoiceType(Route, impl=VARCHAR(length=32)))
    type: Mapped[PaymentType] = mapped_column(
        ChoiceType(PaymentType, impl=VARCHAR(length=32))
    )
    remittance_information_unstructured: Mapped[str] = mapped_column(String(length=512))
    remittance_information_structured: Mapped[str] = mapped_column(
        String(length=512), nullable=True
    )
    short_user_description: Mapped[str] = mapped_column(
        String(length=512), nullable=True
    )
    long_user_description: Mapped[str] = mapped_column(
        String(length=128), nullable=True
    )

    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activity.id"), nullable=True
    )
    activity = relationship("Activity", back_populates="payments", lazy="noload")
    initiative_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("initiative.id"), nullable=True
    )
    initiative = relationship("Initiative", back_populates="payments", lazy="noload")
    debit_card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("debitcard.id"), nullable=True
    )
    debit_card = relationship("DebitCard", back_populates="payments", lazy="noload")
    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bank_account.id"), nullable=True
    )
    bank_account: Mapped[Optional["BankAccount"]] = relationship(
        "BankAccount", back_populates="payments", lazy="noload"
    )


class DebitCard(Base):
    __tablename__ = "debitcard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_number: Mapped[str] = mapped_column(
        String(length=64), unique=True, nullable=False
    )

    initiative_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("initiative.id")
    )
    initiative = relationship("Initiative", back_populates="debit_cards", lazy="noload")
    payments = relationship("Payment", back_populates="debit_card", lazy="noload")


class ReqStatus(str, Enum):
    CREATED = "CR"
    GIVING_CONSENT = "GC"
    UNDERGOING_AUTHENTICATON = "UA"
    REJECTED = "RJ"
    SELECTING_ACCOUNTS = "SA"
    GRANTING_ACCESS = "GA"
    LINKED = "LN"
    SUSPENDED = "SU"
    EXPIRED = "EX"


class Requisition(Base):
    __tablename__ = "requisition"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[str] = mapped_column(String(length=32), nullable=False)
    api_requisition_id: Mapped[str] = mapped_column(String(length=128), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(length=36), nullable=False)
    callback_handled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    status: Mapped[ReqStatus] = mapped_column(
        ChoiceType(ReqStatus, impl=VARCHAR(length=32))
    )

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    user = relationship("User", back_populates="requisitions", lazy="noload")

    bank_accounts: Mapped[list["BankAccount"]] = relationship(
        "BankAccount",
        back_populates="requisitions",
        lazy="noload",
        secondary=requisition_bankaccount,
    )


class BankAccount(Base):
    __tablename__ = "bank_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    iban: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_accessed: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    requisitions: Mapped[list[Requisition]] = relationship(
        "Requisition",
        back_populates="bank_accounts",
        lazy="noload",
        secondary=requisition_bankaccount,
    )

    user_roles = relationship(
        "UserBankAccountRole",
        back_populates="bank_account",
        lazy="noload",
    )
    payments = relationship("Payment", back_populates="bank_account", lazy="noload")
    bank_account_owners = association_proxy("user_roles", "user")


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
