from fastapi import Depends, Request
from ..database import get_user_db, get_async_session
from ..models import User, UserInitiativeRole, UserActivityRole
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
from fastapi_users import models
from fastapi_users.exceptions import UserAlreadyExists
import contextlib
from fastapi_mail import MessageType, FastMail
import os
from ..authorization.authorization import SECRET_KEY
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy.ext.asyncio import AsyncSession


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    def __init__(self, session: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        template = env.get_template("on_after_register.txt")
        body = template.render(user=user)
        message = MessageSchema(
            subject=f"Uitnodiging {os.environ.get('WEBSITE_NAME')}",
            recipients=[user.email],
            body=body,
            subtype=MessageType.plain,
        )
        fm = FastMail(conf)
        await fm.send_message(message)  # TODO: Make async.

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        template = env.get_template("on_after_forgot_password.txt")
        reset_password_url = os.environ.get("SPA_RESET_PASSWORD_URL").format(
            token=token
        )
        body = template.render(user=user, reset_password_url=reset_password_url)
        message = MessageSchema(
            subject=f"Nieuw Wachtwoord {os.environ.get('WEBSITE_NAME')}",
            recipients=[user.email],
            body=body,
            subtype=MessageType.plain,
        )
        fm = FastMail(conf)
        await fm.send_message(message)  # TODO: Make async.

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        try:
            return await super().create(user_create, request=request)
        except UserAlreadyExists:
            raise EntityAlreadyExists(message="Email address already in use")

    async def update(
        self,
        user_update: schemas.UU,
        user: User,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        try:
            return await super().update(user_update, user, request=request)
        except UserAlreadyExists:
            raise EntityAlreadyExists(message="Email address already in use")

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(User)
            .options(
                selectinload(User.bng),
                selectinload(User.initiative_roles).selectinload(
                    UserInitiativeRole.initiative
                ),
                selectinload(User.activity_roles).selectinload(
                    UserActivityRole.activity
                ),
            )
            .where(User.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="User not found")
        return query_result

    async def min_load(self, id: int):
        query_result = await self.session.get(User, id)
        if query_result is None:
            raise EntityNotFound(message="User not found")
        return query_result


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    session: AsyncSession = Depends(get_async_session),
):
    yield UserManager(session, user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)
