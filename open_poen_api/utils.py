from sqlmodel import Session, SQLModel, select
from typing import Type, TypeVar
from fastapi import HTTPException

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
