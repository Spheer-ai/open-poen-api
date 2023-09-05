from fastapi import Request
from ..schemas import PaymentCreateManual, PaymentUpdate, BasePaymentCreate
from ..models import (
    Payment,
    Activity,
    Initiative,
    Grant,
    Regulation,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound
from .base_manager import BaseManager


class PaymentManager(BaseManager):
    async def create(
        self,
        payment_create: PaymentCreateManual,
        initiative_id: int,
        activity_id: int | None,
        request: Request | None,
    ) -> Payment:
        try:
            payment = await self.base_create(
                BasePaymentCreate.parse_obj(payment_create),
                Payment,
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
        payment_db: Payment,
        request: Request | None,
    ) -> Payment:
        try:
            payment = await self.base_update(payment_update, payment_db, request)
        except IntegrityError:
            # Make sure we catch the right error and raise something.
            await self.session.rollback()
        return payment

    async def delete(self, payment: Payment, request: Request | None = None) -> None:
        await self.base_delete(payment, request)

    async def assign_payment_to_initiative(
        self,
        payment: Payment,
        initiative_id: int | None,
        request: Request | None = None,
    ) -> Payment:
        payment.initiative_id = initiative_id
        self.session.add(payment)
        await self.session.commit()
        return payment

    async def assign_payment_to_activity(
        self, payment: Payment, activity_id: int | None, request: Request | None = None
    ) -> Payment:
        payment.activity_id = activity_id
        self.session.add(payment)
        await self.session.commit()
        return payment

    async def detail_load(self, id: int):
        query_result_q = await self.session.execute(
            select(Payment)
            .options(
                selectinload(Payment.activity).selectinload(Activity.user_roles),
                selectinload(Payment.initiative).options(
                    selectinload(Initiative.user_roles),
                    selectinload(Initiative.grant).options(
                        selectinload(Grant.overseer_roles),
                        selectinload(Grant.regulation).options(
                            selectinload(Regulation.policy_officer_roles),
                            selectinload(Regulation.grant_officer_roles),
                        ),
                    ),
                ),
            )
            .where(Payment.id == id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Payment not found")
        return query_result

    async def min_load(self, payment_id: int):
        return await self.base_min_load(Payment, payment_id)
