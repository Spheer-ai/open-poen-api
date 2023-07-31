from ..schemas_and_models.models import entities as ent
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from .utils import client


async def process_requisition(session: AsyncSession, requisition: ent.Requisition):
    api_requisition = client.requisition.get_requisition_by_id(
        requisition.api_requisition_id
    )

    requisition.status = ent.ReqStatus(api_requisition["status"])
    if not requisition.status == ent.ReqStatus.LINKED:
        # The requisition is no longer valid.
        # TODO: Log.
        return

    for account in api_requisition["accounts"]:
        pass


async def get_gocardless_payments(
    session: AsyncSession, requisition_id: int | None = None
):
    if requisition_id is not None:
        requisition_q = await session.execute(
            select(ent.Requisition).where(
                and_(
                    ent.Requisition.id == requisition_id,
                    ent.Requisition.status == ent.ReqStatus.LINKED,
                )
            )
        )
        requisition = requisition_q.scalars().first()
        if not requisition:
            raise ValueError("No linked Requisition found")
        await process_requisition(session, requisition)
    else:
        requisition_q_list = (
            select(ent.Requisition)
            .where(ent.Requisition.status == ent.ReqStatus.LINKED)
            .execution_options(yield_per=256)
        )
        for requisition in await session.scalars(requisition_q_list):
            await process_requisition(session, requisition)
