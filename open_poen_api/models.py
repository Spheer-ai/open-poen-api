from sqlmodel import SQLModel, Field, Column, VARCHAR, Relationship
from datetime import datetime
from pydantic import EmailStr, BaseModel


class InitiativeToUser(SQLModel, table=True):
    initiative_id: int | None = Field(
        default=None, foreign_key="initiative.id", primary_key=True
    )
    user_id: int | None = Field(default=None, foreign_key="user.id", primary_key=True)


class UserBase(SQLModel):
    email: EmailStr = Field(sa_column=Column("email", VARCHAR, unique=True))


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    first_name: str | None
    last_name: str | None
    hashed_password: str
    initiatives: list["Initiative"] = Relationship(
        back_populates="initiative_owners", link_model=InitiativeToUser
    )


class UserCreateReturn(UserBase):
    id: int
    plain_password: str


class UserUpdate(UserBase):
    id: int
    first_name: str | None
    last_name: str | None


class TempUser(BaseModel):
    users: list[UserUpdate]


class InitiativeCreate(SQLModel):
    name: str
    initiative_owners: list[EmailStr]


class Initiative(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    initiative_owners: list[User] = Relationship(
        back_populates="initiatives", link_model=InitiativeToUser
    )


class ActivityBase(SQLModel):
    name: str
    date_of_creation: datetime


class Activity(ActivityBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
