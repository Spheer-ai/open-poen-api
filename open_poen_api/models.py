from sqlmodel import SQLModel, Field
from datetime import datetime


class ActivityBase(SQLModel):
    name: str
    date_of_creation: datetime


class Activity(ActivityBase, table=True):
    id: int = Field(default=None, primary_key=True)
