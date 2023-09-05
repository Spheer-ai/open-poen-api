from sqlalchemy.ext.asyncio import AsyncSession
from .exc import EntityNotFound
from ..models import Base, User
from typing import Type, TypeVar
from pydantic import BaseModel
from fastapi import Request
from ..logger import audit_logger
from typing import Dict, Any

T = TypeVar("T", bound=Base)


class BaseManagerExCurrentUser:
    def __init__(self, session: AsyncSession, current_user: User | None = None):
        self.session = session
        self.current_user = current_user

    async def base_create(
        self,
        entity_create: BaseModel,
        db_model: Type[T],
        request: Request | None = None,
        **kwargs,
    ) -> T:
        entity = db_model(**entity_create.dict(), **kwargs)
        self.session.add(entity)
        await self.session.commit()
        await self.after_create(entity, request)
        return entity

    async def base_update(
        self, entity_update: BaseModel, db_entity: T, request: Request | None = None
    ) -> T:
        update_dict = entity_update.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_entity, key, value)
        self.session.add(db_entity)
        await self.session.commit()
        await self.after_update(db_entity, update_dict, request)
        return db_entity

    async def base_delete(self, entity: T, request: Request | None = None) -> None:
        await self.session.delete(entity)
        await self.session.commit()
        await self.after_delete(entity, request)

    async def base_min_load(self, db_model: Type[T], id: int) -> T:
        query_result = await self.session.get(db_model, id)
        if query_result is None:
            raise EntityNotFound(message=f"{db_model.__name__} not found")
        return query_result

    async def after_create(self, entity: T, request: Request | None):
        audit_logger.info(f"{self.current_user} is creating an entity.")
        audit_logger.info(f"{entity} is created.")

    async def after_update(
        self, entity: T, update_dict: Dict[str, Any], request: Request | None
    ):
        audit_logger.info(f"{self.current_user} is updating an entity.")
        audit_logger.info(f"{entity} is updated with {update_dict}.")

    async def after_delete(self, entity: T, request: Request | None):
        audit_logger.info(f"{self.current_user} is deleting an entity.")
        audit_logger.info(f"{entity} is deleted.")
