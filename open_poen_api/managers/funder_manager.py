from .base_manager import Manager
from ..schemas import FunderCreate, FunderUpdate
from ..models import Funder
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from fastapi import Depends


class FunderManager(Manager):
    async def create(
        self, funder_create: FunderCreate, request: Request | None = None
    ) -> Funder:
        try:
            funder = await self.base_create(funder_create, Funder, request)
        except IntegrityError:
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return funder

    async def update(
        self,
        funder_update: FunderUpdate,
        funder_db: Funder,
        request: Request | None = None,
    ) -> Funder:
        try:
            funder = await self.base_update(funder_update, funder_db, request)
        except:
            IntegrityError
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return funder

    async def delete(self, funder: Funder, request: Request | None = None) -> None:
        await self.base_delete(funder, request)

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Funder)
            .options(selectinload(Funder.regulations))
            .where(Funder.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Funder not found")
        return query_result

    async def min_load(self, id: int) -> Funder:
        return await self.base_min_load(Funder, id)


async def get_funder_manager(session: AsyncSession = Depends(get_async_session)):
    yield FunderManager(session)
