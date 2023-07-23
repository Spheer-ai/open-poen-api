from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from ..database import get_async_session


class ActivityAlreadyExists(BaseException):
    pass


class ActivityManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_and_verify():
        pass

    async def create():
        pass

    async def update():
        pass

    async def delete():
        pass

    async def make_users_owner():
        pass


async def get_activity_manager(session: AsyncSession = Depends(get_async_session)):
    yield ActivityManager(session)
