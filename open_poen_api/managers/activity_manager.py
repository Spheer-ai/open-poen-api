from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, UploadFile
from ..database import get_async_session
from ..schemas import ActivityCreate, ActivityUpdate
from .. import models as ent
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..exc import EntityNotFound, raise_err_if_unique_constraint
from .base_manager import BaseManager
from .handlers import ProfilePictureHandler
from .user_manager.user_manager_ex_current_user import optional_login


class ActivityManager(BaseManager):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: ent.User | None = Depends(optional_login),
    ):
        super().__init__(session, current_user)
        self.profile_picture_handler = ProfilePictureHandler[ent.Activity](
            self.session, current_user, ent.AttachmentEntityType.ACTIVITY
        )

    async def create(
        self,
        activity_create: ActivityCreate,
        initiative_id: int,
        request: Request | None = None,
    ) -> ent.Activity:
        try:
            activity = await self.crud.create(
                activity_create, ent.Activity, request, initiative_id=initiative_id
            )
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique activity name per initiative", e)
            raise
        return activity

    async def update(
        self,
        activity_update: ActivityUpdate,
        activity_db: ent.Activity,
        request: Request | None = None,
    ) -> ent.Activity:
        try:
            activity = await self.crud.update(activity_update, activity_db, request)
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique activity name per initiative", e)
            raise
        return activity

    async def delete(
        self, activity: ent.Activity, request: Request | None = None
    ) -> None:
        await self.crud.delete(activity, request)

    async def make_users_owner(
        self,
        activity: ent.Activity,
        user_ids: list[int],
        request: Request | None = None,
    ):
        linked_user_ids = {role.user_id for role in activity.user_roles}

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
            role for role in activity.user_roles if role.user_id in unlink_user_ids
        ]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = ent.UserActivityRole(user_id=user_id, activity_id=activity.id)
            self.session.add(new_role)

        await self.session.commit()
        return activity

    async def detail_load(self, activity_id: int):
        query_result_q = await self.session.execute(
            select(ent.Activity)
            .options(
                selectinload(ent.Activity.user_roles).joinedload(
                    ent.UserActivityRole.user
                ),
            )
            .where(ent.Activity.id == activity_id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Activity not found")
        return query_result

    async def min_load(self, activity_id: int) -> ent.Activity:
        return await self.load.min_load(ent.Activity, activity_id)
