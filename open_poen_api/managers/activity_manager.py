from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from ..database import get_async_session
from ..schemas_and_models import ActivityCreate
from ..schemas_and_models.models.entities import Activity
from sqlalchemy.exc import IntegrityError


class ActivityAlreadyExists(BaseException):
    pass


class ActivityManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_and_verify():
        pass

    async def create(
        self,
        activity_create: ActivityCreate,
        initiative_id: int,
        request: Request | None = None,
    ) -> Activity:
        activity = Activity(initiative_id=initiative_id, **activity_create.dict())
        self.session.add(activity)
        try:
            await self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise ActivityAlreadyExists
        return activity

    async def update():
        pass

    async def delete():
        pass

    async def make_users_owner():
        pass


async def get_activity_manager(session: AsyncSession = Depends(get_async_session)):
    yield ActivityManager(session)
