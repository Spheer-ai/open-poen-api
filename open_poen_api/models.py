from sqlmodel import SQLModel, Field, Column, VARCHAR, Relationship, UniqueConstraint
from datetime import datetime
from pydantic import EmailStr, BaseModel
from enum import Enum
from sqlalchemy_utils import ChoiceType
from sqlalchemy import Column, Integer, ForeignKey


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
    ADMIN = "admin"
    FINANCIAL = "financial"
    USER = "user"


class UserBase(SQLModel):
    email: EmailStr = Field(sa_column=Column("email", VARCHAR, unique=True, index=True))
    first_name: str | None
    last_name: str | None
    biography: str | None
    role: Role = Field(
        sa_column=Column(ChoiceType(Role, impl=VARCHAR(length=32))),
        nullable=False,
        default=Role.USER,
    )
    hidden: bool = Field(nullable=False, default=False)
    active: bool = Field(nullable=False, default=True)
    image: str | None


class User(UserBase, table=True):
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


class UserOut(UserBase):
    id: int


class UserOutList(BaseModel):
    users: list[UserOut]


# INITIATIVE
class InitiativeBase(SQLModel):
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
    hidden: bool = Field(nullable=False, default=False)
    hidden_sponsors = Field(nullable=False, default=False)


class Initiative(InitiativeBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    initiative_owners: list[User] = Relationship(
        back_populates="initiatives", link_model=InitiativeToUser
    )
    activities: list["Activity"] = Relationship(
        back_populates="initiative",
        sa_relationship_kwargs={"cascade": "all,delete,delete-orphan"},
    )


class InitiativeIn(InitiativeBase):
    initiative_owner_ids: list[int] | None
    activity_ids: list[int] | None


class InitiativeOut(InitiativeBase):
    id: int


class InitiativeOutList(BaseModel):
    initiatives: list[InitiativeOut]


# ACTIVITY
class ActivityBase(SQLModel):
    name: str
    description: str
    purpose: str
    target_audience: str
    image: str | None
    hidden: bool = Field(nullable=False, default=False)
    # budget
    finished_description: str | None
    finished: bool = Field(nullable=False, default=False)


class Activity(ActivityBase, table=True):
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

    __table_args__ = (
        UniqueConstraint("name", "initiative_id", name="unique_activity_name"),
    )


class ActivityIn(ActivityBase):
    activity_owner_ids: list[int] | None


class ActivityOut(ActivityBase):
    id: int


class ActivityOutList(BaseModel):
    activities: list[ActivityOut]


# OUTPUT MODELS WITH LINKED ENTITIES
class InitiativeOutWithLinkedEntities(InitiativeOut):
    initiative_owners: list[UserOut]
    activities: list[ActivityOut]


class UserOutWithLinkedEntities(UserOut):
    initiatives: list[InitiativeOut]
    activities: list[ActivityOut]


class ActivityOutWithLinkedEntities(ActivityOut):
    activity_owners: list[UserOut]
