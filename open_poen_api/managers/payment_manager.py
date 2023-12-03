from fastapi import Request, Depends
from ..schemas import PaymentCreateManual, PaymentUpdate, BasePaymentCreate
from .. import models as ent
from sqlalchemy import select
from ..exc import EntityNotFound
from ..exc import EntityNotFound
from .base_manager import BaseManager
from .handlers import AttachmentHandler
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from .user_manager import optional_login
from sqlalchemy.orm import selectinload


class PaymentManager(BaseManager):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: ent.User | None = Depends(optional_login),
    ):
        super().__init__(session, current_user)
        self.attachment_handler = AttachmentHandler[ent.Payment](
            self.session, current_user, ent.AttachmentEntityType.PAYMENT
        )

    async def create(
        self,
        payment_create: PaymentCreateManual,
        initiative_id: int,
        activity_id: int | None,
        request: Request | None,
    ) -> ent.Payment:
        payment = await self.crud.create(
            BasePaymentCreate.parse_obj(payment_create),
            ent.Payment,
            request,
            initiative_id=initiative_id,
            activity_id=activity_id,
        )
        return payment

    async def update(
        self,
        payment_update: PaymentUpdate,
        payment_db: ent.Payment,
        request: Request | None,
    ) -> ent.Payment:
        payment = await self.crud.update(payment_update, payment_db, request)
        return payment

    async def delete(
        self, payment: ent.Payment, request: Request | None = None
    ) -> None:
        await self.crud.delete(payment, request)

    async def assign_payment_to_initiative(
        self,
        payment: ent.Payment,
        initiative_id: int | None,
        request: Request | None = None,
    ) -> ent.Payment:
        payment.initiative_id = initiative_id
        self.session.add(payment)
        await self.session.commit()
        await self.logger.after_update(
            payment, {"initiative_id": initiative_id}, request=request
        )
        return payment

    async def assign_payment_to_activity(
        self,
        payment: ent.Payment,
        activity_id: int | None,
        request: Request | None = None,
    ) -> ent.Payment:
        payment.activity_id = activity_id
        self.session.add(payment)
        await self.session.commit()
        await self.logger.after_update(
            payment, {"activity_id": activity_id}, request=request
        )
        return payment

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(ent.Payment)
            .options(selectinload(ent.Payment.attachments))
            .where(ent.Payment.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Payment not found")
        return query_result

    async def min_load(self, payment_id: int):
        return await self.load.min_load(ent.Payment, payment_id)
