from .base_manager import BaseManager
from ..schemas import GrantCreate, GrantUpdate
from .. import models as ent
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from ..exc import EntityAlreadyExists, EntityNotFound, raise_err_if_unique_constraint
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


class GrantManager(BaseManager):
    async def create(
        self,
        grant_create: GrantCreate,
        regulation_id: int,
        request: Request | None,
    ) -> ent.Grant:
        try:
            grant = await self.crud.create(
                grant_create,
                ent.Grant,
                request,
                regulation_id=regulation_id,
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique grant names per regulation", e)
            raise
        return grant

    async def update(
        self,
        grant_update: GrantUpdate,
        grant_db: ent.Grant,
        request: Request | None = None,
    ) -> ent.Grant:
        try:
            grant = await self.crud.update(grant_update, grant_db, request)
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique grant names per regulation", e)
            raise
        return grant

    async def delete(self, grant: ent.Grant, request: Request | None = None):
        await self.crud.delete(grant, request)

    async def make_users_overseer(
        self, grant: ent.Grant, user_ids: list[int], request: Request | None = None
    ):
        linked_user_ids = {role.user_id for role in grant.overseer_roles}

        matched_users_q = await self.session.execute(
            select(ent.User).where(ent.User.id.in_(user_ids))
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
            new_role = ent.UserGrantRole(user_id=user_id, grant_id=grant.id)
            self.session.add(new_role)

        await self.session.commit()
        return grant

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.Grant)
            .options(
                joinedload(ent.Grant.regulation),
                selectinload(ent.Grant.initiatives),
                selectinload(ent.Grant.overseer_roles).joinedload(
                    ent.UserGrantRole.user
                ),
            )
            .where(ent.Grant.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Grant not found")
        return query_result

    async def min_load(self, id: int) -> ent.Grant:
        return await self.load.min_load(ent.Grant, id)
