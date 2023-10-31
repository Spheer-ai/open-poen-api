from .base_manager import BaseManager
from ..schemas import GrantCreate, GrantUpdate
from ..models import Grant, UserGrantRole, User, Initiative
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


class GrantManager(BaseManager):
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

    async def make_users_overseer(
        self, grant: Grant, user_ids: list[int], request: Request | None = None
    ):
        linked_user_ids = {role.user_id for role in grant.overseer_roles}

        matched_users_q = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        matched_users = matched_users_q.scalars().all()
        matched_user_ids = {user.id for user in matched_users}

        if not len(matched_users) == len(user_ids):
            raise EntityNotFound(
                message=f"There exist no Users with id's: {set(user_ids) - matched_user_ids}"
            )

        # TODO: Log this.
        stay_linked_user_ids = linked_user_ids.intersection(matched_user_ids)
        unlink_user_ids = linked_user_ids - matched_user_ids
        link_user_ids = matched_user_ids - linked_user_ids

        for role in [
            role for role in grant.overseer_roles if role.user_id in unlink_user_ids
        ]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = UserGrantRole(user_id=user_id, grant_id=grant.id)
            self.session.add(new_role)

        await self.session.commit()
        return grant

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Grant)
            .options(
                selectinload(Grant.regulation),
                selectinload(Grant.initiatives),
                selectinload(Grant.overseer_roles).selectinload(UserGrantRole.user),
            )
            .where(Grant.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Grant not found")
        return query_result

    async def min_load(self, id: int) -> Grant:
        return await self.base_min_load(Grant, id)
