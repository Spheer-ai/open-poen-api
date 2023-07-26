from ..database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException
from ..schemas_and_models.models.entities import Initiative, User, UserInitiativeRole
from ..schemas_and_models import InitiativeCreate, InitiativeUpdate
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class InitiativeManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, initiative_create: InitiativeCreate, request: Request | None = None
    ) -> Initiative:
        initiative = Initiative(**initiative_create.dict())
        self.session.add(initiative)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
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
            await self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
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
        existing_roles = await self.session.execute(
            select(UserInitiativeRole).where(
                UserInitiativeRole.initiative_id == initiative.id
            )
        )
        existing_roles = existing_roles.scalars().all()
        existing_role_user_ids = {i.user_id for i in existing_roles}

        existing_users = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        existing_users = existing_users.scalars().all()
        existing_user_ids = {i.id for i in existing_users}

        if not len(existing_users) == len(user_ids):
            raise EntityNotFound(
                message=f"There exist no Users with id's: {set(user_ids) - existing_user_ids}"
            )

        for role in [
            role for role in existing_roles if role.user_id not in existing_user_ids
        ]:
            await self.session.delete(role)

        for user_id in [
            user_id
            for user_id in existing_user_ids
            if user_id not in existing_role_user_ids
        ]:
            new_role = UserInitiativeRole(user_id=user_id, initiative_id=initiative.id)
            self.session.add(new_role)

        await self.session.commit()
        return initiative

    async def detail_load(self, id: int):
        query_result = await self.session.execute(
            select(Initiative)
            .options(
                selectinload(Initiative.user_roles).selectinload(
                    UserInitiativeRole.user
                ),
                selectinload(Initiative.activities),
            )
            .where(Initiative.id == id)
        )
        query_result = query_result.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Initiative not found")
        return query_result

    async def min_load(self, id: int):
        query_result = await self.session.get(Initiative, id)
        if query_result is None:
            raise EntityNotFound(message="Initiative not found")
        return query_result


async def get_initiative_manager(session: AsyncSession = Depends(get_async_session)):
    yield InitiativeManager(session)
