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
    Activity,
    Initiative,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, delete, or_
from sqlalchemy.orm import selectinload, joinedload
from .exc import EntityNotFound
from .exc import EntityAlreadyExists, EntityNotFound
from .base_manager import BaseManager
import asyncio
from ..gocardless import get_nordigen_client
from nordigen import NordigenClient
from nordigen.types import Requisition
from ..database import get_async_session
from .user_manager import optional_login
from aiohttp import ClientResponseError
from ..logger import audit_logger


class BankAccountManager(BaseManager):
    def __init__(
        self,
        session: AsyncSession = Depends(get_async_session),
        current_user: User | None = Depends(optional_login),
        client: NordigenClient = Depends(get_nordigen_client),
    ):
        self.client = client
        super().__init__(session, current_user)

    async def revoke(self, bank_account: BankAccount, request: Request | None):
        for req in bank_account.requisitions:
            try:
                if req.status not in (ReqStatus.REVOKED, ReqStatus.DELETED):
                    await self.client.requisition.delete_requisition(
                        req.api_requisition_id
                    )
            except ClientResponseError as e:
                if e.code != 404:
                    raise
                audit_logger.warning(
                    f"On revoking {bank_account} an API requisition could not be "
                    "deleted because it was not found. This can happen if the user "
                    "coupled two bank accounts with one requisition."
                )
            req.status = ReqStatus.REVOKED
            self.session.add(req)

        await self.session.execute(
            delete(Payment).where(
                and_(
                    Payment.bank_account_id == bank_account.id,
                    Payment.initiative_id == None,
                )
            )
        )

        await self.session.commit()
        await self.session.refresh(bank_account)
        return bank_account

    async def delete(self, bank_account: BankAccount, request: Request | None):
        for req in bank_account.requisitions:
            try:
                if req.status not in (ReqStatus.REVOKED, ReqStatus.DELETED):
                    await self.client.requisition.delete_requisition(
                        req.api_requisition_id
                    )
            except ClientResponseError as e:
                if e.code != 404:
                    raise
                audit_logger.warning(
                    f"On deleting {bank_account} an API requisition could not be "
                    "deleted because it was not found. This can happen if the user "
                    "coupled two bank accounts with one requisition."
                )
            req.status = ReqStatus.DELETED
            self.session.add(req)

        # TODO: Make sure an error is returned if there are payments for this bank
        # account that are coupled to a finished or justified activity or initiative.
        await self.session.execute(
            delete(Payment).where(
                Payment.bank_account_id == bank_account.id,
                or_(
                    Payment.initiative_id == None,
                    and_(
                        Payment.initiative_id != None,
                        Payment.initiative.has(Initiative.justified == False),
                    ),
                ),
                or_(
                    Payment.activity_id == None,
                    and_(
                        Payment.activity_id != None,
                        Payment.activity.has(Activity.finished == False),
                    ),
                ),
            )
        )

        await self.session.delete(bank_account)
        await self.session.commit()

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
                selectinload(BankAccount.user_roles)
                .joinedload(UserBankAccountRole.user)
                .joinedload(User.profile_picture),
                selectinload(BankAccount.owner_role)
                .selectinload(UserBankAccountRole.user)
                .joinedload(User.profile_picture),
            )
            .where(BankAccount.id == bank_account_id)
        )
        query_result = query_result_q.scalars().first()
        if query_result is None:
            raise EntityNotFound(message="Bank account not found")
        return query_result

    async def min_load(self, bank_account_id: int):
        return await self.base_min_load(BankAccount, bank_account_id)
