from sqlmodel import Session, SQLModel, select, col
from typing import Type, TypeVar
from fastapi import HTTPException
import os
from dotenv import load_dotenv
import string
import random

load_dotenv()

DEBUG = os.getenv("DEBUG") == "true"


T = TypeVar("T", bound=SQLModel)


def get_entities_by_ids(
    session: Session, model: Type[T], entity_ids: list[int]
) -> list[T]:
    """Helper function that's useful to check that all ids of model that the user
    wants to link to an entity actually exist. Is used when a user created an initiatives
    and wants to links users to it by id for example."""
    entities = session.exec(select(model).where(model.id.in_(entity_ids))).all()

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


def get_fields_dict(model: SQLModel) -> dict:
    """An input schema can have ids of entities for which we want to establish
    a relationship. Those we process separately, so we filter those out here."""
    fields_dict = {}
    for key, value in model.dict().items():
        if not key.endswith("_ids"):
            fields_dict[key] = value
    return fields_dict
