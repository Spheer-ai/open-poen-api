from .base_manager import Manager
from ..schemas import GrantCreate, GrantUpdate
from ..models import Grant
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from fastapi import Depends


class GrantManager(Manager):
    async def create(
        self,
        grant_create: GrantCreate,
        funder_id: int,
        regulation_id: int,
        request: Request | None,
    ) -> Grant:
        try:
            grant = await self.base_create(
                grant_create,
                Grant,
                request,
                funder_id=funder_id,
                regulation_id=regulation_id,
            )
        except IntegrityError:
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return grant

    async def update(
        self,
        grant_update: GrantUpdate,
        grant_db: Grant,
        request: Request | None = None,
    ) -> Grant:
        try:
            grant = await self.base_update(grant_update, grant_db, request)
        except:
            IntegrityError
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return grant

    async def delete(self, grant: Grant, request: Request | None = None):
        await self.base_delete(grant, request)

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Grant)
            .options(
                selectinload(Grant.regulation),
                selectinload(Grant.initiatives),
            )
            .where(Grant.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Grant not found")
        return query_result

    async def min_load(self, id: int) -> Grant:
        return await self.base_min_load(Grant, id)


async def get_grant_manager(session: AsyncSession = Depends(get_async_session)):
    yield GrantManager(session)
