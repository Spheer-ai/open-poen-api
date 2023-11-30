from fastapi import Request
from ..schemas import PaymentCreateManual, PaymentUpdate, BasePaymentCreate
from .. import models as ent
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from ..exc import EntityNotFound
from ..exc import EntityNotFound
from .base_manager import BaseManager


class PaymentManager(BaseManager):
    async def create(
        self,
        payment_create: PaymentCreateManual,
        initiative_id: int,
        activity_id: int | None,
        request: Request | None,
    ) -> ent.Payment:
        try:
            payment = await self.crud.create(
                BasePaymentCreate.parse_obj(payment_create),
                ent.Payment,
                request,
                initiative_id=initiative_id,
                activity_id=activity_id,
            )
        except IntegrityError:
            # TODO: Make sure we catch the right error.
            # TODO: Raise an error?
            await self.session.rollback()
        return payment

    async def update(
        self,
        payment_update: PaymentUpdate,
        payment_db: ent.Payment,
        request: Request | None,
    ) -> ent.Payment:
        try:
            payment = await self.crud.update(payment_update, payment_db, request)
        except IntegrityError:
            # Make sure we catch the right error and raise something.
            await self.session.rollback()
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
            select(ent.Payment).where(ent.Payment.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Payment not found")
        return query_result

    async def min_load(self, payment_id: int):
        return await self.load.min_load(ent.Payment, payment_id)
