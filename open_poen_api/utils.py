from sqlmodel import Session, SQLModel, select
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
    if not hasattr(model, "id"):
        raise ValueError(f"Model {model} does not have an id attribute/column.")

    entities = session.exec(select(model).where(model.id.in_(entity_ids))).all()

    if len(entities) != len(entity_ids):
        raise HTTPException(
            status_code=404,
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
