from .base_manager import Manager
from ..schemas import RegulationCreate, RegulationUpdate
from ..models import Regulation, UserRegulationRole, User, RegulationRole
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from fastapi import Depends
from typing import Literal


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
            raise EntityAlreadyExists(message="Name is already in u4se")
        return regulation

    async def delete(self, regulation: Regulation, request: Request | None = None):
        await self.base_delete(regulation, request)

    async def make_users_officer(
        self,
        regulation: Regulation,
        user_ids: list[int],
        regulation_role: RegulationRole,
        request: Request | None = None,
    ):
        if regulation_role == RegulationRole.GRANT_OFFICER:
            officer_roles = regulation.grant_officer_roles
            role_field = RegulationRole.GRANT_OFFICER
        elif regulation_role == RegulationRole.POLICY_OFFICER:
            officer_roles = regulation.policy_officer_roles
            role_field = RegulationRole.POLICY_OFFICER
        else:
            raise ValueError(f"Unknown RegulationRole: {regulation_role}")

        linked_user_ids = {role.user_id for role in officer_roles}

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

        for role in [role for role in officer_roles if role.user_id in unlink_user_ids]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = UserRegulationRole(
                user_id=user_id,
                regulation_id=regulation.id,
                role=role_field,
            )
            self.session.add(new_role)

        await self.session.commit()
        return regulation

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
