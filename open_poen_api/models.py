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
from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
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
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), primary_key=True
    )
    initiative_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("initiative.id"), primary_key=True
    )
    user: Mapped["User"] = relationship("User", back_populates="initiative_roles")
    initiative: Mapped["Initiative"] = relationship(
        "Initiative", back_populates="user_roles"
    )


class UserActivityRole(Base):
    __tablename__ = "user_activity_roles"
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), primary_key=True
    )
    activity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("activity.id"), primary_key=True
    )
    user: Mapped["User"] = relationship("User", back_populates="activity_roles")
    activity: Mapped["Activity"] = relationship("Activity", back_populates="user_roles")


class BankAccountRole(str, Enum):
    OWNER = "owner"
    USER = "user"


class UserBankAccountRole(Base):
    __tablename__ = "user_bank_account_roles"
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), primary_key=True
    )
    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bank_account.id"), primary_key=True
    )
    role: Mapped[BankAccountRole] = mapped_column(
        ChoiceType(BankAccountRole, impl=VARCHAR(length=32))
    )

    user: Mapped["User"] = relationship("User")
    bank_account: Mapped["BankAccount"] = relationship("BankAccount")


class RegulationRole(str, Enum):
    GRANT_OFFICER = "grant officer"
    POLICY_OFFICER = "policy officer"


class UserRegulationRole(Base):
    __tablename__ = "user_regulation_roles"
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), primary_key=True
    )
    regulation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regulation.id"), primary_key=True
    )
    role: Mapped[RegulationRole] = mapped_column(
        ChoiceType(RegulationRole, impl=VARCHAR(length=32))
    )

    user: Mapped["User"] = relationship("User")
    regulation: Mapped["Regulation"] = relationship("Regulation")


class UserRole(str, Enum):
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
    role: Mapped[UserRole] = mapped_column(
        ChoiceType(UserRole, impl=VARCHAR(length=32))
    )
    image: Mapped[str | None] = mapped_column(String(length=128))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    bng: Mapped[Optional["BNG"]] = relationship(
        "BNG", uselist=False, back_populates="user", lazy="noload"
    )
    requisitions: Mapped[list["Requisition"]] = relationship(
        "Requisition", back_populates="user", lazy="noload"
    )

    initiative_roles: Mapped[list[UserInitiativeRole]] = relationship(
        "UserInitiativeRole",
        back_populates="user",
        lazy="noload",
    )
    initiatives: AssociationProxy[list["Initiative"]] = association_proxy(
        "initiative_roles", "initiative"
    )
    activity_roles: Mapped[list[UserActivityRole]] = relationship(
        "UserActivityRole",
        back_populates="user",
        lazy="noload",
    )
    activities: AssociationProxy[list["Activity"]] = association_proxy(
        "activity_roles", "activity"
    )

    user_bank_account_roles: Mapped[list[UserBankAccountRole]] = relationship(
        "UserBankAccountRole",
        lazy="noload",
        primaryjoin=f"and_(User.id==UserBankAccountRole.user_id, UserBankAccountRole.role=='{BankAccountRole.USER.value}')",
        overlaps="owner_bank_account_role, user",
    )
    used_bank_accounts: AssociationProxy[list["BankAccount"]] = association_proxy(
        "user_bank_account_roles", "bank_account"
    )

    owner_bank_account_role: Mapped[list[UserBankAccountRole]] = relationship(
        "UserBankAccountRole",
        lazy="noload",
        primaryjoin=f"and_(User.id==UserBankAccountRole.user_id, UserBankAccountRole.role=='{BankAccountRole.OWNER.value}')",
        overlaps="user_bank_account_roles, user",
    )
    owned_bank_account: AssociationProxy[list["BankAccount"]] = association_proxy(
        "owner_bank_account_role", "bank_account"
    )

    grant_officer_regulation_roles: Mapped[list[UserRegulationRole]] = relationship(
        "UserRegulationRole",
        lazy="noload",
        primaryjoin=f"and_(User.id==UserRegulationRole.user_id, UserRegulationRole.role=='{RegulationRole.GRANT_OFFICER.value}')",
        overlaps="policy_officer_regulation_roles, user",
    )
    grant_officer_regulations: AssociationProxy[list["Regulation"]] = association_proxy(
        "grant_officer_regulation_roles", "regulation"
    )

    policy_officer_regulation_roles: Mapped[list[UserRegulationRole]] = relationship(
        "UserRegulationRole",
        lazy="noload",
        primaryjoin=f"and_(User.id==UserRegulationRole.user_id, UserRegulationRole.role=='{RegulationRole.POLICY_OFFICER.value}')",
        overlaps="grant_officer_regulation_roles, user",
    )
    policy_officer_regulations: AssociationProxy[
        list["Regulation"]
    ] = association_proxy("policy_officer_regulation_roles", "regulation")

    def __repr__(self):
        return f"User(id={self.id}, name='{self.first_name} {self.last_name}', role='{self.role}', is_superuser='{self.is_superuser}')"

    REL_FIELDS = [
        "bng",
        "requisitions",
        "initiative_roles",
        "initiatives",
        "activity_roles",
        "activities",
        "shared_bank_account_roles",
        "shared_bank_accounts",
        "owned_bank_account_role",
        "owned_bank_account",
        "grant_officer_regulation_roles",
        "grant_officer_regulation_roles",
        "grant_officer_regulations",
        "policy_officer_regulation_roles",
        "policy_officer_regulations",
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
    user: Mapped[User] = relationship(
        "User", back_populates="bng", lazy="noload", uselist=False
    )

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
    budget: Mapped[Decimal] = mapped_column(DECIMAL(precision=8, scale=2))

    user_roles: Mapped[list[UserInitiativeRole]] = relationship(
        "UserInitiativeRole",
        back_populates="initiative",
        lazy="noload",
        cascade="delete",
    )
    initiative_owners: AssociationProxy[list[User]] = association_proxy(
        "user_roles", "user"
    )
    activities: Mapped[list["Activity"]] = relationship(
        "Activity", back_populates="initiative", lazy="noload", cascade="delete"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="initiative", lazy="noload"
    )
    debit_cards: Mapped[list["DebitCard"]] = relationship(
        "DebitCard", back_populates="initiative", lazy="noload"
    )
    grant_id: Mapped[int] = mapped_column(Integer, ForeignKey("grant.id"))
    grant: Mapped["Grant"] = relationship(
        "Grant", back_populates="initiatives", lazy="noload", uselist=False
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
    budget: Mapped[Decimal] = mapped_column(DECIMAL(precision=8, scale=2))

    user_roles: Mapped[list[UserActivityRole]] = relationship(
        "UserActivityRole",
        back_populates="activity",
        lazy="noload",
    )
    activity_owners: AssociationProxy[list[User]] = association_proxy(
        "user_roles", "user"
    )
    initiative_id: Mapped[int] = mapped_column(Integer, ForeignKey("initiative.id"))
    initiative: Mapped[Initiative] = relationship(
        "Initiative", back_populates="activities", lazy="noload", uselist=False
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="activity", lazy="noload"
    )

    def __repr__(self):
        return f"Activity(id={self.id}, name='{self.name}')"


class Route(str, Enum):
    """We need to distinguish between incoming and outcoming funds, so that
    we can take corrective payments into account in the calculation rules, such
    as refunds."""

    INCOME = "inkomen"
    EXPENSES = "uitgaven"


class PaymentType(str, Enum):
    BNG = "BNG"
    GOCARDLESS = "GoCardless"
    MANUAL = "handmatig"


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
    activity: Mapped[Optional[Activity]] = relationship(
        "Activity", back_populates="payments", lazy="noload", uselist=False
    )
    initiative_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("initiative.id"), nullable=True
    )
    initiative: Mapped[Optional[Initiative]] = relationship(
        "Initiative", back_populates="payments", lazy="noload", uselist=False
    )
    debit_card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("debitcard.id"), nullable=True
    )
    debit_card: Mapped[Optional["DebitCard"]] = relationship(
        "DebitCard", back_populates="payments", lazy="noload", uselist=False
    )
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
    initiative: Mapped[Initiative | None] = relationship(
        "Initiative", back_populates="debit_cards", lazy="noload", uselist=False
    )
    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="debit_card", lazy="noload"
    )


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
    # Defined by us, not Gocardless. Indicates that the requisition was done for a bank
    # account that was requisitioned earlier by another user.
    CONFLICTED = "CO"


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

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
    user: Mapped[User] = relationship(
        "User", back_populates="requisitions", lazy="noload", uselist=False
    )

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

    user_roles: Mapped[list[UserBankAccountRole]] = relationship(
        "UserBankAccountRole",
        lazy="noload",
        primaryjoin=f"and_(BankAccount.id==UserBankAccountRole.bank_account_id, UserBankAccountRole.role=='{BankAccountRole.USER.value}')",
        overlaps="owner_role, bank_account",
    )
    users: AssociationProxy[list[User]] = association_proxy("user_roles", "user")

    owner_role: Mapped[UserBankAccountRole] = relationship(
        "UserBankAccountRole",
        lazy="noload",
        primaryjoin=f"and_(BankAccount.id==UserBankAccountRole.bank_account_id, UserBankAccountRole.role=='{BankAccountRole.OWNER.value}')",
        uselist=False,
        overlaps="user_roles, bank_account",
    )
    owner: AssociationProxy[User] = association_proxy("owner_role", "user")

    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="bank_account", lazy="noload"
    )


class Regulation(Base):
    __tablename__ = "regulation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(512), nullable=False)

    grant_officer_roles: Mapped[list[UserRegulationRole]] = relationship(
        "UserRegulationRole",
        lazy="noload",
        primaryjoin=f"and_(Regulation.id==UserRegulationRole.regulation_id, UserRegulationRole.role=='{RegulationRole.GRANT_OFFICER.value}')",
        overlaps="policy_officer_roles, regulation",
    )
    grant_officers: AssociationProxy[list[User]] = association_proxy(
        "grant_officer_roles", "user"
    )

    policy_officer_roles: Mapped[list[UserRegulationRole]] = relationship(
        "UserRegulationRole",
        lazy="noload",
        primaryjoin=f"and_(Regulation.id==UserRegulationRole.regulation_id, UserRegulationRole.role=='{RegulationRole.POLICY_OFFICER.value}')",
        overlaps="grant_officer_roles, regulation",
    )
    policy_officers: AssociationProxy[list[User]] = association_proxy(
        "policy_officer_roles", "user"
    )

    grants: Mapped[list["Grant"]] = relationship(
        "Grant", back_populates="regulation", lazy="noload"
    )
    funder_id: Mapped[int] = mapped_column(Integer, ForeignKey("funder.id"))
    funder: Mapped["Funder"] = relationship(
        "Funder", back_populates="regulations", lazy="noload", uselist=False
    )


class Grant(Base):
    __tablename__ = "grant"
    __table_args__ = (
        UniqueConstraint("name", "regulation_id", name="_name_regulation_uc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    budget: Mapped[Decimal] = mapped_column(DECIMAL(precision=8, scale=2))

    regulation_id: Mapped[int] = mapped_column(Integer, ForeignKey("regulation.id"))
    regulation: Mapped[Regulation] = relationship(
        "Regulation", back_populates="grants", lazy="noload", uselist=False
    )
    initiatives: Mapped[list[Initiative]] = relationship(
        "Initiative", back_populates="grant", lazy="noload"
    )


class Funder(Base):
    __tablename__ = "funder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(512))

    regulations: Mapped[list[Regulation]] = relationship(
        "Regulation", back_populates="funder", lazy="noload"
    )
