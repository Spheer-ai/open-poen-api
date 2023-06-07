from sqlmodel import SQLModel, Field, Column, VARCHAR
from datetime import datetime
from pydantic import EmailStr


class UserBase(SQLModel):
    username: EmailStr = Field(sa_column=Column("username", VARCHAR, unique=True))


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # TODO: Let users fill these in on first login.
    first_name: str | None
    last_name: str | None
    hashed_password: str


class UserReturn(UserBase):
    plain_password: str


class ActivityBase(SQLModel):
    name: str
    date_of_creation: datetime


class Activity(ActivityBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
