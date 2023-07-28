from typing import Type, TypeVar, Any
from fastapi import HTTPException, Request
import os
import string
import random
from ..schemas_and_models.models import entities as ent
from .. import schemas_and_models as s
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .load_env import load_env_vars
import datetime

load_env_vars()

DEBUG = os.environ.get("ENVIRONMENT") == "debug"


def get_requester_ip(request: Request):
    if request.client is not None:
        return request.client.host
    else:
        return "123.456.789.101"


def format_user_timestamp(user_id: int | None) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
    formatted_string = f"{user_id}_{timestamp}"
    return formatted_string


def temp_password_generator(
    size: int = 10, chars=string.ascii_uppercase + string.digits
) -> str:
    if not DEBUG:
        return "".join(random.choice(chars) for _ in range(size))
    else:
        return "DEBUG_PASSWORD"
