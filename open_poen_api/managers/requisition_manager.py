from ..database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request, HTTPException
from ..models import Requisition
from ..schemas import InitiativeCreate, InitiativeUpdate
from sqlalchemy.exc import IntegrityError
from .exc import EntityAlreadyExists, EntityNotFound
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .base_manager import Manager
import asyncio
from ..gocardless import client


class RequisitionManager(Manager):
    def __init__(self, session: AsyncSession, client):
        self.client = client
        super().__init__(session)

    async def delete(
        self, requisition: Requisition, request: Request | None = None
    ) -> None:
        await self._delete_requisition_in_thread(requisition.api_requisition_id)
        await self.base_delete(requisition, request=request)

    async def _delete_requisition_in_thread(self, api_requisition_id):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.requisition.delete_requisition, api_requisition_id
        )

    async def min_load(self, id: int) -> Requisition:
        return await self.base_min_load(Requisition, id)


async def get_requisition_manager(session: AsyncSession = Depends(get_async_session)):
    yield RequisitionManager(session, client)
