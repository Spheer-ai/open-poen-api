from fastapi import Depends, Request, UploadFile
from ..database import get_user_db, get_async_session
from ..models import (
    User,
    UserInitiativeRole,
    UserActivityRole,
    UserBankAccountRole,
    UserRegulationRole,
    UserGrantRole,
    Attachment,
    AttachmentEntityType,
    AttachmentAttachmentType,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from ..utils.email import MessageSchema, conf, env
from ..utils.utils import upload_profile_picture, ProfilePictureUpdate
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
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy.ext.asyncio import AsyncSession
from .base_manager_ex_current_user import BaseManagerExCurrentUser
from typing import Any, Dict, cast
from pydantic import EmailStr


WEBSITE_NAME = os.environ["WEBSITE_NAME"]
SPA_RESET_PASSWORD_URL = os.environ["SPA_RESET_PASSWORD_URL"]


class UserManagerExCurrentUser(
    IntegerIDMixin,
    BaseUserManager[User, int],
    BaseManagerExCurrentUser,
):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    def __init__(self, session: AsyncSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    async def on_after_register(self, user: User, request: Optional[Request] = None):
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
        await fm.send_message(message)  # TODO: Make async.
        await self.after_create(user, request)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
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

    async def on_after_update(
        self,
        user: User,
        update_dict: Dict[str, Any],
        request: Request | None = None,
    ):
        await self.after_update(user, update_dict, request)

    async def on_after_delete(
        self,
        user: User,
        request: Request | None = None,
    ):
        await self.after_delete(user, request)

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(User)
            .options(
                selectinload(User.requisitions),
                selectinload(User.initiative_roles).joinedload(
                    UserInitiativeRole.initiative
                ),
                selectinload(User.activity_roles).joinedload(UserActivityRole.activity),
                selectinload(User.user_bank_account_roles).joinedload(
                    UserBankAccountRole.bank_account
                ),
                selectinload(User.owner_bank_account_roles).joinedload(
                    UserBankAccountRole.bank_account
                ),
                selectinload(User.grant_officer_regulation_roles).joinedload(
                    UserRegulationRole.regulation
                ),
                selectinload(User.policy_officer_regulation_roles).joinedload(
                    UserRegulationRole.regulation
                ),
                selectinload(User.overseer_roles).joinedload(UserGrantRole.grant),
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

    async def set_profile_picture(
        self, file: UploadFile, user: User, request: Request | None = None
    ) -> None:
        filename = f"{user.id}_user_profile_picture"
        profile_picture_update = await upload_profile_picture(file, filename)
        user.profile_picture = Attachment(
            entity_id=user.id,
            entity_type=AttachmentEntityType.USER,
            attachment_type=AttachmentAttachmentType.PROFILE_PICTURE,
            raw_attachment_url=profile_picture_update.raw_image_url,
        )
        self.session.add(user)
        await self.session.commit()
        # await self.base_update(profile_picture_update, user, request=request)

    async def unset_profile_picture(
        self, user: User, request: Request | None = None
    ) -> None:
        profile_picture_update = ProfilePictureUpdate(
            raw_image_url=None, raw_image_thumbnail_url=None
        )
        await self.base_update(profile_picture_update, user, request=request)


async def _get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    session: AsyncSession = Depends(get_async_session),
):
    yield UserManagerExCurrentUser(session, user_db)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, int](_get_user_manager, [auth_backend])

get_user_manager_context = contextlib.asynccontextmanager(_get_user_manager)


def with_joins(original_dependency):
    async def _user_with_extra_joins(
        user=Depends(original_dependency),
        user_manager: UserManagerExCurrentUser = Depends(_get_user_manager),
    ):
        if user is None:
            return None

        detail_user = await user_manager.detail_load(user.id)
        return detail_user

    return _user_with_extra_joins


superuser = with_joins(fastapi_users.current_user(superuser=True))
required_login = with_joins(fastapi_users.current_user(optional=False))
optional_login = with_joins(fastapi_users.current_user(optional=True))


class UserManager(UserManagerExCurrentUser):
    def __init__(
        self,
        user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
    ):
        super().__init__(session, user_db)
        self.current_user = current_user
