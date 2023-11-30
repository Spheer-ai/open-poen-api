from fastapi import Depends
from ...database import get_user_db, get_async_session
from ... import models as ent
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from fastapi_users.db import SQLAlchemyUserDatabase
from ...exc import EntityNotFound
from sqlalchemy.ext.asyncio import AsyncSession
from ..handlers import ProfilePictureHandler
from ..base_manager import BaseManager
from .user_manager_ex_current_user import UserManagerExCurrentUser, optional_login


class UserManager(BaseManager, UserManagerExCurrentUser):
    def __init__(
        self,
        user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
        session: AsyncSession = Depends(get_async_session),
        current_user: ent.User | None = Depends(optional_login),
    ):
        BaseManager.__init__(self, session, current_user)
        UserManagerExCurrentUser.__init__(self, session, user_db, current_user)
        self.profile_picture_handler = ProfilePictureHandler[ent.User](
            session, current_user, ent.AttachmentEntityType.USER
        )

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.User)
            .options(
                selectinload(ent.User.initiative_roles).joinedload(
                    ent.UserInitiativeRole.initiative
                ),
                selectinload(ent.User.activity_roles).joinedload(
                    ent.UserActivityRole.activity
                ),
                selectinload(ent.User.user_bank_account_roles).joinedload(
                    ent.UserBankAccountRole.bank_account
                ),
                selectinload(ent.User.owner_bank_account_roles).joinedload(
                    ent.UserBankAccountRole.bank_account
                ),
                selectinload(ent.User.grant_officer_regulation_roles).joinedload(
                    ent.UserRegulationRole.regulation
                ),
                selectinload(ent.User.policy_officer_regulation_roles).joinedload(
                    ent.UserRegulationRole.regulation
                ),
                selectinload(ent.User.overseer_roles).joinedload(
                    ent.UserGrantRole.grant
                ),
                joinedload(ent.User.profile_picture),
            )
            .where(ent.User.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="User not found")
        return query_result

    async def min_load(self, user_id: int) -> ent.User:
        return await self.load.min_load(ent.User, user_id)
