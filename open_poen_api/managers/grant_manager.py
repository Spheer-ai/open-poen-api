from .base_manager import Manager
from ..schemas import GrantCreate, GrantUpdate
from ..models import Grant, UserGrantRole, User
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
        regulation_id: int,
        request: Request | None,
    ) -> Grant:
        try:
            grant = await self.base_create(
                grant_create,
                Grant,
                request,
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
        except IntegrityError:
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return grant

    async def delete(self, grant: Grant, request: Request | None = None):
        await self.base_delete(grant, request)

    async def make_user_overseer(
        self, grant: Grant, user_id: int | None, request: Request | None = None
    ):
        if user_id is None:
            if grant.overseer_role is None:
                return grant
            else:
                await self.session.delete(grant.overseer_role)
        else:
            q = await self.session.execute(select(User).where(User.id == user_id))
            if q.scalars().first() is None:
                raise EntityNotFound(message=f"There exists no User with id {user_id}")
            if grant.overseer_role is None:
                role = UserGrantRole(user_id=user_id, grant_id=grant.id)
                self.session.add(role)
            else:
                grant.overseer_role.user_id = user_id
                self.session.add(grant)
        await self.session.commit()
        return grant

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Grant)
            .options(
                selectinload(Grant.regulation),
                selectinload(Grant.initiatives),
                selectinload(Grant.overseer_role).selectinload(UserGrantRole.user),
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
