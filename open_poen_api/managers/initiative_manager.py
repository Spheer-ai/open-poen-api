from ..database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException
from ..schemas_and_models.models.entities import Initiative, User
from ..schemas_and_models import InitiativeCreate, InitiativeUpdate
from sqlalchemy.exc import IntegrityError
from ..utils.utils import get_entities_by_ids


class InitiativeAlreadyExists(BaseException):
    pass


class InitiativeManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_and_verify(self, id: int) -> Initiative:
        initiative = await self.session.get(Initiative, id)
        if not initiative:
            raise HTTPException(status_code=404, detail="Initiative not found")
        return initiative

    async def create(
        self, initiative_create: InitiativeCreate, request: Request | None = None
    ) -> Initiative:
        initiative = Initiative(**initiative_create.dict())
        self.session.add(initiative)
        try:
            await self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise InitiativeAlreadyExists
        return initiative

    async def update(
        self,
        initiative_update: InitiativeUpdate,
        initiative_db: Initiative,
        request: Request | None = None,
    ) -> Initiative:
        for key, value in initiative_update.dict(exclude_unset=True).items():
            setattr(initiative_db, key, value)
        self.session.add(initiative_db)
        try:
            await self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise InitiativeAlreadyExists
        return initiative_db

    async def delete(
        self, initiative: Initiative, request: Request | None = None
    ) -> None:
        await self.session.delete(initiative)
        await self.session.commit()

    async def make_users_owner(
        self,
        initiative: Initiative,
        user_ids: list[int],
        request: Request | None = None,
    ):
        users = await get_entities_by_ids(self.session, User, user_ids)
        initiative.initiative_owners = users
        self.session.add(initiative)
        await self.session.commit()
        return initiative


async def get_initiative_manager(session: AsyncSession = Depends(get_async_session)):
    yield InitiativeManager(session)
