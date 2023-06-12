from sqlmodel import SQLModel, Field, Column, VARCHAR, Relationship
from datetime import datetime
from pydantic import EmailStr, BaseModel
from enum import Enum
from sqlalchemy_utils import ChoiceType


class InitiativeToUser(SQLModel, table=True):
    initiative_id: int | None = Field(
        default=None, foreign_key="initiative.id", primary_key=True
    )
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)


class Role(str, Enum):
    ADMIN = "admin"
    FINANCIAL = "financial"
    USER = "user"


class UserBase(SQLModel):
    email: EmailStr = Field(sa_column=Column("email", VARCHAR, unique=True))
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


class UserCreateIn(UserBase):
    initiative_ids: list[int] | None


class UserUpdateIn(UserBase):
    initiative_ids: list[int] | None


class UserOut(UserBase):
    id: int


class UserOutList(BaseModel):
    users: list[UserOut]


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


class InitiativeCreateIn(InitiativeBase):
    initiative_owner_ids: list[int] | None


class InitiativeUpdateIn(InitiativeBase):
    initiative_owner_ids: list[int] | None


class InitiativeOut(InitiativeBase):
    id: int


class InitiativeOutWithOwners(InitiativeOut):
    initiative_owners: list[UserOut]


class UserOutWithInitiatives(UserOut):
    initiatives: list[InitiativeOut]
