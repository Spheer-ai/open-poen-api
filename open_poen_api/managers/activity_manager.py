from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from ..database import get_async_session
from ..schemas_and_models import ActivityCreate, ActivityUpdate
from ..schemas_and_models.models.entities import (
    Activity,
    UserActivityRole,
    User,
    Initiative,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound


class ActivityManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        activity_create: ActivityCreate,
        initiative_id: int,
        request: Request | None = None,
    ) -> Activity:
        activity = Activity(initiative_id=initiative_id, **activity_create.dict())
        self.session.add(activity)
        try:
            await self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise EntityAlreadyExists(message="Name is already in use")
        return activity

    async def update(
        self,
        activity_update: ActivityUpdate,
        activity_db: Activity,
        request: Request | None = None,
    ) -> Activity:
        for key, value in activity_update.dict(exclude_unset=True).items():
            setattr(activity_db, key, value)
        self.session.add(activity_db)
        try:
            await self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise EntityAlreadyExists("Name is already in use")
        return activity_db

    async def delete(self, activity: Activity, request: Request | None = None) -> None:
        await self.session.delete(activity)
        await self.session.commit()

    async def make_users_owner(
        self, activity: Activity, user_ids: list[int], request: Request | None = None
    ):
        existing_roles = await self.session.execute(
            select(UserActivityRole).where(UserActivityRole.activity_id == activity.id)
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
            new_role = UserActivityRole(user_id=user_id, activity_id=activity.id)
            self.session.add(new_role)

        await self.session.commit()
        return activity

    async def detail_load(self, initiative_id: int, activity_id: int):
        query_result = await self.session.execute(
            select(Activity)
            .options(
                selectinload(Activity.user_roles).selectinload(UserActivityRole.user),
                selectinload(Activity.initiative),
            )
            .where(and_(Initiative.id == initiative_id, Activity.id == activity_id))
        )
        query_result = query_result.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Activity not found")
        return query_result

    async def min_load(self, initiative_id: int, activity_id: int):
        query_result = await self.session.execute(
            select(Activity).where(
                and_(Initiative.id == initiative_id, Activity.id == activity_id)
            )
        )
        query_result = query_result.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Activity not found")
        return query_result


async def get_activity_manager(session: AsyncSession = Depends(get_async_session)):
    yield ActivityManager(session)
