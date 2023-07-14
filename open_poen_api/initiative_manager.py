from .database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from .schemas_and_models.models.entities import Initiative
from .schemas_and_models import InitiativeCreate, InitiativeUpdate
from sqlalchemy.exc import IntegrityError


class InitiativeAlreadyExists(BaseException):
    pass


class InitiativeManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, initiative_create: InitiativeCreate, request: Request | None = None
    ) -> Initiative:
        initiative = Initiative(initiative_create.dict())
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


async def get_initiative_manager(session: AsyncSession = Depends(get_async_session)):
    yield InitiativeManager(session)
