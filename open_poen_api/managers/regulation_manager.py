from .base_manager import Manager
from ..schemas import RegulationCreate, RegulationUpdate
from ..models import Regulation, UserRegulationRole
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from fastapi import Depends


class RegulationManager(Manager):
    async def create(
        self,
        regulation_create: RegulationCreate,
        funder_id: int,
        request: Request | None,
    ) -> Regulation:
        try:
            regulation = await self.base_create(
                regulation_create, Regulation, request, funder_id=funder_id
            )
        except IntegrityError:
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return regulation

    async def update(
        self,
        regulation_update: RegulationUpdate,
        regulation_db: Regulation,
        request: Request | None = None,
    ) -> Regulation:
        try:
            regulation = await self.base_update(
                regulation_update, regulation_db, request
            )
        except:
            IntegrityError
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return regulation

    async def delete(self, regulation: Regulation, request: Request | None = None):
        await self.base_delete(regulation, request)

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Regulation)
            .options(
                selectinload(Regulation.grant_officer_roles).selectinload(
                    UserRegulationRole.user
                ),
                selectinload(Regulation.policy_officer_roles).selectinload(
                    UserRegulationRole.user
                ),
                selectinload(Regulation.grants),
                selectinload(Regulation.funder),
            )
            .where(Regulation.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Regulation not found")
        return query_result

    async def min_load(self, id: int) -> Regulation:
        return await self.base_min_load(Regulation, id)


async def get_regulation_manager(session: AsyncSession = Depends(get_async_session)):
    yield RegulationManager(session)
