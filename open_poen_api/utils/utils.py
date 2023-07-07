from typing import Type, TypeVar, Any
from fastapi import HTTPException, Request
import os
import string
import random
from ..schemas_and_models.models import entities as ent
from .. import schemas_and_models as s
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncSession

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
    formatted_string = f"{user_id}-{timestamp}"
    return formatted_string


T = TypeVar("T", bound=DeclarativeBase)


async def get_entities_by_ids(
    session: AsyncSession, model: Type[T], entity_ids: list[int]
) -> list[T]:
    """Helper function that's useful to check that all ids of model that the user
    wants to link to an entity actually exist. Is used when a user created an initiatives
    and wants to links users to it by id for example."""
    entities = await session.exec(select(model).where(model.id.in_(entity_ids))).all()

    if len(entities) != len(entity_ids):
        raise HTTPException(
            status_code=404,
            # TODO: Specify which ids are missing.
            # TODO: Separate error if duplicate ids.
            detail=f"One or more instances of {model.__name__} to link do not exist",
        )

    return entities


def temp_password_generator(
    size: int = 10, chars=string.ascii_uppercase + string.digits
) -> str:
    if not DEBUG:
        return "".join(random.choice(chars) for _ in range(size))
    else:
        return "DEBUG_PASSWORD"


def get_fields_dict(d: dict) -> dict:
    """An input schema can have ids of entities for which we want to establish
    a relationship. Those we process separately, so we filter those out here."""
    fields_dict = {}
    for key, value in d.items():
        if not key.endswith("_ids"):
            fields_dict[key] = value
    return fields_dict
