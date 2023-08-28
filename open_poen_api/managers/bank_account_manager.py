from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from ..database import get_async_session
from ..schemas import ActivityCreate, ActivityUpdate
from ..models import BankAccount, Payment, UserBankAccountRole, User, BankAccountRole
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound
from .base_manager import Manager
import asyncio
from ..gocardless import client


class BankAccountManager(Manager):
    def __init__(self, session: AsyncSession, client):
        self.client = client
        super().__init__(session)

    async def delete(self, bank_account: BankAccount, request: Request | None) -> None:
        # Delete all payments of this bank account that have not been assigned to an
        # initiative yet. (Payments assigned to an activity also have the initiative
        # relationship).
        await self.session.execute(
            delete(Payment).where(
                and_(
                    Payment.bank_account_id == bank_account.id,
                    Payment.initiative_id == None,
                )
            )
        )
        # Revoke all requisitions through the api for this bank account.
        for req in bank_account.requisitions:
            await self._delete_requisition_in_thread(req.api_requisition_id)
        # This will delete the requisitions through a cascade.
        await self.base_delete(bank_account, request=request)

    async def _delete_requisition_in_thread(self, api_requisition_id):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.requisition.delete_requisition, api_requisition_id
        )

    async def make_users_user(
        self,
        bank_account: BankAccount,
        user_ids: list[int],
        request: Request | None = None,
    ):
        linked_user_ids = {role.user_id for role in bank_account.user_roles}

        matched_users_q = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        matched_users = matched_users_q.scalars().all()
        matched_user_ids = {user.id for user in matched_users}

        if not len(matched_users) == len(user_ids):
            raise EntityNotFound(
                message=f"There exist no Users with id's: {set(user_ids) - matched_user_ids}"
            )

        # TODO: Log this.
        stay_linked_user_ids = linked_user_ids.intersection(matched_user_ids)
        unlink_user_ids = linked_user_ids - matched_user_ids
        link_user_ids = matched_user_ids - linked_user_ids

        for role in [
            role for role in bank_account.user_roles if role.user_id in unlink_user_ids
        ]:
            await self.session.delete(role)

        for user_id in link_user_ids:
            new_role = UserBankAccountRole(
                user_id=user_id, activity_id=bank_account.id, role=BankAccountRole.USER
            )
            self.session.add(new_role)

        await self.session.commit()
        return bank_account

    async def detail_load(self, bank_account_id: int):
        query_result_q = await self.session.execute(
            select(BankAccount)
            .options(
                selectinload(BankAccount.requisitions),
                selectinload(BankAccount.user_roles).selectinload(
                    UserBankAccountRole.user
                ),
                selectinload(BankAccount.owner_role).selectinload(
                    UserBankAccountRole.user
                ),
            )
            .where(BankAccount.id == bank_account_id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Bank account not found")
        return query_result


async def get_bank_account_manager(session: AsyncSession = Depends(get_async_session)):
    yield BankAccountManager(session, client)
