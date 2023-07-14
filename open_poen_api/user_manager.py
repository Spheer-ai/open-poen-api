from fastapi import Depends, Request
from .database import get_user_db
from .schemas_and_models.models.entities import User
from .utils.load_env import load_env_vars
from .utils.email import MessageSchema, conf, env
import os
from fastapi_users import BaseUserManager, IntegerIDMixin, FastAPIUsers
from typing import Optional
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.authentication import (
    BearerTransport,
    JWTStrategy,
    AuthenticationBackend,
)
import contextlib
from fastapi_mail import MessageType, FastMail
import os
from oso import Oso

load_env_vars()


oso = Oso()
oso.register_class(User)
oso.load_file("open_poen_api/main.polar")


SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

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
        await fm.send_message(message)  # Make async.

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
        await fm.send_message(message)  # Make async.


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET_KEY, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt", transport=bearer_transport, get_strategy=get_jwt_strategy
)


fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)

get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)
