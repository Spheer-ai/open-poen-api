from .base_manager import BaseManager
from ..schemas import FunderCreate, FunderUpdate
from .. import models as ent
from fastapi import Request
from sqlalchemy.exc import IntegrityError
from ..exc import EntityAlreadyExists, EntityNotFound, raise_err_if_unique_constraint
from sqlalchemy import select
from sqlalchemy.orm import selectinload


class FunderManager(BaseManager):
    async def create(
        self, funder_create: FunderCreate, request: Request | None = None
    ) -> ent.Funder:
        try:
            funder = await self.crud.create(funder_create, ent.Funder, request)
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique_funder_name", e)
            raise
        return funder

    async def update(
        self,
        funder_update: FunderUpdate,
        funder_db: ent.Funder,
        request: Request | None = None,
    ) -> ent.Funder:
        try:
            funder = await self.crud.update(funder_update, funder_db, request)
        except IntegrityError as e:
            raise_err_if_unique_constraint("unique funder name", e)
            raise
        return funder

    async def delete(self, funder: ent.Funder, request: Request | None = None) -> None:
        await self.crud.delete(funder, request)

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.Funder)
            .options(selectinload(ent.Funder.regulations))
            .where(ent.Funder.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Funder not found")
        return query_result

    async def min_load(self, id: int) -> ent.Funder:
        return await self.load.min_load(ent.Funder, id)
