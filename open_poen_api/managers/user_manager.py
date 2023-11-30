from fastapi import Depends, Request, Response

from open_poen_api.models import User
from ..database import get_user_db, get_async_session
from .. import models as ent
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..utils.email import MessageSchema, conf, env
import os
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from typing import Optional
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication import (
    BearerTransport,
    JWTStrategy,
    AuthenticationBackend,
)
from fastapi_users import schemas
from fastapi_users.exceptions import UserAlreadyExists
import contextlib
from fastapi_mail import MessageType, FastMail
import os
from ..authorization.authorization import SECRET_KEY
from ..exc import EntityAlreadyExists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_
from .base_manager_ex_current_user import BaseLogger
from typing import Any, Dict, cast
from pydantic import EmailStr
from ..logger import audit_logger


WEBSITE_NAME = os.environ["WEBSITE_NAME"]
SPA_RESET_PASSWORD_URL = os.environ["SPA_RESET_PASSWORD_URL"]


class UserManagerExCurrentUser(
    IntegerIDMixin,
    BaseUserManager[ent.User, int],
    BaseLogger,
):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY
    user_db: SQLAlchemyUserDatabase

    def __init__(self, session: AsyncSession, user_db, current_user=None):
        BaseUserManager.__init__(self, user_db)
        BaseLogger.__init__(self, session, current_user)

    async def on_after_register(
        self, user: ent.User, request: Optional[Request] = None
    ):
        email = cast(EmailStr, user.email)
        template = env.get_template("on_after_register.txt")
        body = template.render(user=user)
        message = MessageSchema(
            subject=f"Uitnodiging {WEBSITE_NAME}",
            recipients=[email],
            body=body,
            subtype=MessageType.plain,
        )
        fm = FastMail(conf)
        await fm.send_message(message)
        await self.after_create(user, request)
        audit_logger.info(f"{user} has been registered.")

    async def on_after_forgot_password(
        self, user: ent.User, token: str, request: Optional[Request] = None
    ):
        email = cast(EmailStr, user.email)
        template = env.get_template("on_after_forgot_password.txt")
        reset_password_url = SPA_RESET_PASSWORD_URL.format(token=token)
        body = template.render(user=user, reset_password_url=reset_password_url)
        message = MessageSchema(
            subject=f"Nieuw Wachtwoord {WEBSITE_NAME}",
            recipients=[email],
            body=body,
            subtype=MessageType.plain,
        )
        fm = FastMail(conf)
        await fm.send_message(message)
        audit_logger.info(f"{user} has requested a new password.")

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        audit_logger.info(f"{user} has logged in.")

    async def on_after_reset_password(
        self, user: User, request: Request | None = None
    ) -> None:
        audit_logger.info(f"{user} has reset his or her password.")

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Request | None = None,
    ) -> ent.User:
        try:
            return await super().create(user_create, request=request)
        except UserAlreadyExists:
            raise EntityAlreadyExists(message="Email address already in use")

    async def update(
        self,
        user_update: schemas.UU,
        user: ent.User,
        safe: bool = False,
        request: Request | None = None,
    ) -> ent.User:
        try:
            return await super().update(user_update, user, request=request)
        except UserAlreadyExists:
            raise EntityAlreadyExists(message="Email address already in use")

    async def on_after_update(
        self,
        user: ent.User,
        update_dict: Dict[str, Any],
        request: Request | None = None,
    ):
        await self.after_update(user, update_dict, request)

    async def on_after_delete(
        self,
        user: ent.User,
        request: Request | None = None,
    ):
        await self.after_delete(user, request)

    async def requesting_user_load(self, id: int):
        query_result_q = await self.user_db.session.execute(
            select(ent.User)
            .options(
                selectinload(ent.User.initiative_roles),
                selectinload(ent.User.activity_roles),
                selectinload(ent.User.user_bank_account_roles),
                selectinload(ent.User.owner_bank_account_roles),
                selectinload(ent.User.grant_officer_regulation_roles),
                selectinload(ent.User.policy_officer_regulation_roles),
                selectinload(ent.User.overseer_roles),
            )
            .where(ent.User.id == id)
            .execution_options(populate_existing=True)
        )
        user = query_result_q.scalars().one()
        return user


async def _get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    session: AsyncSession = Depends(get_async_session),
):
    yield UserManagerExCurrentUser(session, user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=60 * 60 * 10)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[ent.User, int](_get_user_manager, [auth_backend])

get_user_manager_context = contextlib.asynccontextmanager(_get_user_manager)


def with_joins(original_dependency):
    async def _user_with_extra_joins(
        user=Depends(original_dependency),
        user_manager: UserManagerExCurrentUser = Depends(_get_user_manager),
    ):
        if user is None:
            return None

        user = await user_manager.requesting_user_load(user.id)
        # This expunge is important to prevent the data on this user from being
        # manipulated and or erased after another instance is queried that shares
        # data with this user instance. SQL-Alchemy optimization it seems.
        user_manager.session.expunge(user)
        return user

    return _user_with_extra_joins


superuser = with_joins(fastapi_users.current_user(superuser=True))
required_login = with_joins(fastapi_users.current_user(optional=False))
optional_login = with_joins(fastapi_users.current_user(optional=True))
