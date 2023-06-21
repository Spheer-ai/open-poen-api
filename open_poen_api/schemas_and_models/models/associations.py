from sqlmodel import SQLModel, Field


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
