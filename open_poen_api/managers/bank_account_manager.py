from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, Request
from ..database import get_async_session
from ..schemas import ActivityCreate, ActivityUpdate
from ..models import (
    BankAccount,
    Payment,
    UserBankAccountRole,
    User,
    BankAccountRole,
    ReqStatus,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound
from .base_manager import BaseManager
import asyncio
from ..gocardless import get_nordigen_client
from nordigen import NordigenClient
from nordigen.types import Requisition
from ..database import get_async_session
from .user_manager import optional_login


class BankAccountManager(BaseManager):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
        client: NordigenClient = Depends(get_nordigen_client),
    ):
        self.client = client
        super().__init__(session, current_user)

    # TODO: Prevent blocking of event loop here.
    async def finish(self, bank_account: BankAccount, request: Request | None):
        await self.session.execute(
            delete(Payment).where(
                and_(
                    Payment.bank_account_id == bank_account.id,
                    Payment.initiative_id == None,
                )
            )
        )

        for req in bank_account.requisitions:
            api_req = await self._get_requisition_in_thread(req.api_requisition_id)
            for api_user_agreement_id in api_req.agreements:
                await self._delete_user_agreement_in_thread(api_user_agreement_id)
            await self._delete_requisition_in_thread(req.api_requisition_id)
            req.status = ReqStatus.REVOKED
            self.session.add(req)

        await self.session.commit()
        await self.session.refresh(bank_account)
        return bank_account

    async def delete(self, bank_account: BankAccount, request: Request | None):
        # TODO: What if it's linked to a justified or finished initiative / activity?
        await self.session.execute(
            delete(Payment).where(Payment.bank_account_id == bank_account.id)
        )

        for req in bank_account.requisitions:
            api_req = await self._get_requisition_in_thread(req.api_requisition_id)
            for api_user_agreement_id in api_req.agreements:
                await self._delete_user_agreement_in_thread(api_user_agreement_id)
            await self._delete_requisition_in_thread(req.api_requisition_id)
            req.status = ReqStatus.REVOKED
            self.session.add(req)

        await self.session.commit()
        await self.base_delete(bank_account, request=request)

    async def _delete_requisition_in_thread(self, api_requisition_id):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.requisition.delete_requisition, api_requisition_id
        )

    async def _get_requisition_in_thread(self, api_requisition_id) -> Requisition:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.requisition.get_requisition_by_id, api_requisition_id
        )

    async def _delete_user_agreement_in_thread(self, api_user_agreement_id):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.client.agreement.delete_agreement, api_user_agreement_id
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
                user_id=user_id,
                bank_account_id=bank_account.id,
                role=BankAccountRole.USER,
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

    async def min_load(self, bank_account_id: int):
        return await self.base_min_load(BankAccount, bank_account_id)
