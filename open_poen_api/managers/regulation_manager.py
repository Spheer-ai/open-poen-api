from .base_manager import BaseManager
from ..schemas import RegulationCreate, RegulationUpdate
from .. import models as ent
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from ..exc import EntityAlreadyExists, EntityNotFound, raise_err_if_unique_constraint
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


class RegulationManager(BaseManager):
    async def create(
        self,
        regulation_create: RegulationCreate,
        funder_id: int,
        request: Request | None,
    ) -> ent.Regulation:
        try:
            regulation = await self.crud.create(
                regulation_create, ent.Regulation, request, funder_id=funder_id
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique regulation names per funder", e)
            raise
        return regulation

    async def update(
        self,
        regulation_update: RegulationUpdate,
        regulation_db: ent.Regulation,
        request: Request | None = None,
    ) -> ent.Regulation:
        try:
            regulation = await self.crud.update(
                regulation_update, regulation_db, request
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique regulation names per funder", e)
            raise
        return regulation

    async def delete(self, regulation: ent.Regulation, request: Request | None = None):
        await self.crud.delete(regulation, request)

    async def make_users_officer(
        self,
        regulation: ent.Regulation,
        user_ids: list[int],
        regulation_role: ent.RegulationRole,
        request: Request | None = None,
    ):
        if regulation_role == ent.RegulationRole.GRANT_OFFICER:
            officer_roles = regulation.grant_officer_roles
            role_field = ent.RegulationRole.GRANT_OFFICER
        elif regulation_role == ent.RegulationRole.POLICY_OFFICER:
            officer_roles = regulation.policy_officer_roles
            role_field = ent.RegulationRole.POLICY_OFFICER
        else:
            raise ValueError(f"Unknown RegulationRole: {regulation_role}")

        linked_user_ids = {role.user_id for role in officer_roles}

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

        for role in [role for role in officer_roles if role.user_id in unlink_user_ids]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = ent.UserRegulationRole(
                user_id=user_id,
                regulation_id=regulation.id,
                role=role_field,
            )
            self.session.add(new_role)

        await self.session.commit()
        return regulation

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.Regulation)
            .options(
                selectinload(ent.Regulation.grant_officer_roles).joinedload(
                    ent.UserRegulationRole.user
                ),
                selectinload(ent.Regulation.policy_officer_roles).joinedload(
                    ent.UserRegulationRole.user
                ),
                selectinload(ent.Regulation.grants),
                joinedload(ent.Regulation.funder),
            )
            .where(ent.Regulation.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Regulation not found")
        return query_result

    async def min_load(self, id: int) -> ent.Regulation:
        return await self.load.min_load(ent.Regulation, id)
