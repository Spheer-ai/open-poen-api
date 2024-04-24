from .. import models as ent
from sqlalchemy import select, and_, inspect, not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from .utils import get_nordigen_client, get_institutions
from datetime import datetime, timedelta
from collections.abc import MutableMapping
from dateutil.parser import parse
import re
from decimal import Decimal
from sqlalchemy.orm import selectinload
from asyncio import sleep
from ..database import async_session_maker
from ..logger import audit_logger
from .payment_schema import Payment, AccountMetadata, AccountDetails
from typing import Sequence
from aiohttp import ClientResponseError

# Retrieve payments in chunks of N days.
PAYMENT_RETRIEVAL_INTERVAL = 14
# Don't process requisitions with these statuses. Requisitions with
# statuses will never again become valid for payment retrieval.
EXCLUDED_STATUSES = [
    ent.ReqStatus.SUSPENDED,
    ent.ReqStatus.EXPIRED,
    ent.ReqStatus.CONFLICTED,
    ent.ReqStatus.REVOKED,
]


def should_be_skipped(
    account: ent.BankAccount | None,
    account_api_id: str,
    metadata: AccountMetadata,
    processed_accounts: set[str],
):
    # Skip if the account is 1) already processed, or 2) is not ready. If any of these
    # is not true, add the account to the set of processed accounts and continue to
    # process it.
    account_log_str = (
        account if account else f"unsaved account with api id {account_api_id}"
    )
    if account_api_id in processed_accounts:
        audit_logger.info(f"Skipping {account_log_str} because it's already processed.")
        return True
    elif metadata.status != "READY":
        audit_logger.info(f"Skipping {account_log_str} because it's not ready.")
        return True
    else:
        audit_logger.info(f"Processing {account_log_str}.")
        processed_accounts.add(account_api_id)
        return False


async def process_requisition(
    session: AsyncSession,
    requisition: ent.Requisition,
    date_from: datetime,
    processed_accounts: set[str],
):
    client = await get_nordigen_client()
    institutions = await get_institutions()

    try:
        api_requisition = await client.requisition.get_requisition_by_id(
            requisition.api_requisition_id
        )
    except ClientResponseError as e:
        if e.status == 404:
            audit_logger.info(f"Requisition not found for {requisition}.")
            return
        else:
            raise
    await sleep(0.5)

    requisition.status = ent.ReqStatus(api_requisition["status"])
    await session.commit()

    if not requisition.status == ent.ReqStatus.LINKED:
        audit_logger.info(
            f"Skipping {requisition} because of its status {requisition.status}."
        )
        return

    for account_api_id in api_requisition["accounts"]:
        api_account = client.account_api(account_api_id)
        metadata = await api_account.get_metadata()
        parsed_metadata = AccountMetadata(**metadata)
        await sleep(0.5)
        details = await api_account.get_details()
        parsed_details = AccountDetails(**details)
        await sleep(0.5)

        if parsed_metadata.id is None:
            audit_logger.info(
                f"Skipping account with id {account_api_id} because its parsed metadata id is None."
            )
            continue

        account_q = await session.execute(
            select(ent.BankAccount)
            .where(ent.BankAccount.api_account_id == parsed_metadata.id)
            .options(
                selectinload(ent.BankAccount.requisitions),
                selectinload(ent.BankAccount.user_roles).selectinload(
                    ent.UserBankAccountRole.user
                ),
                selectinload(ent.BankAccount.owner_role).selectinload(
                    ent.UserBankAccountRole.user
                ),
            )
        )
        account = account_q.scalars().first()

        if should_be_skipped(
            account, account_api_id, parsed_metadata, processed_accounts
        ):
            continue

        if not account:
            account = ent.BankAccount(
                api_account_id=parsed_metadata.id,
                iban=parsed_metadata.iban,
                name=parsed_details.get_name(),
                created=parsed_metadata.created,
                last_accessed=parsed_metadata.last_accessed,
                institution_id=parsed_metadata.institution_id,
                institution_name=institutions.get_name(metadata["institution_id"]),
                institution_logo=institutions.get_logo(metadata["institution_id"]),
                requisitions=[requisition],
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            new_role = ent.UserBankAccountRole(
                user_id=requisition.user_id,
                bank_account_id=account.id,
                role=ent.BankAccountRole.OWNER,
            )
            session.add(new_role)
            await session.commit()
        else:
            if requisition.user is not account.owner:
                # In this case a third user requisitioned this bank account earlier.
                requisition.status = ent.ReqStatus.CONFLICTED
                await session.commit()
            if requisition not in account.requisitions:
                account.requisitions.append(requisition)
            account.last_accessed = parsed_metadata.last_accessed
            await session.commit()

        date_to = datetime.now()
        cur_start_date = date_from
        async with async_session_maker() as payment_session:
            while cur_start_date < date_to:
                cur_end_date = min(
                    cur_start_date + timedelta(days=PAYMENT_RETRIEVAL_INTERVAL), date_to
                )
                audit_logger.info(
                    f"Retrieving payments for user {requisition.user} with period {cur_start_date.strftime('%Y-%m-%d')} till {cur_end_date.strftime('%Y-%m-%d')}."
                )
                api_transactions = await api_account.get_transactions(
                    date_from=cur_start_date.strftime("%Y-%m-%d"),
                    date_to=cur_end_date.strftime("%Y-%m-%d"),
                )
                await sleep(0.5)

                skipped, imported = 0, 0
                for payment in api_transactions["transactions"]["booked"]:
                    parsed_payment = Payment(**payment)
                    if parsed_payment.transaction_id is None:
                        audit_logger.warning(
                            f"Skipping a parsed payment {parsed_payment} because its transaction_id is None."
                        )
                        continue
                    new_payment = ent.Payment(
                        **parsed_payment.to_dict(),
                        bank_account_id=account.id,
                    )

                    payment_session.add(new_payment)
                    try:
                        await payment_session.commit()
                    except IntegrityError as e:
                        if "unique transaction id" in str(e):
                            audit_logger.info(
                                f"Skipping a parsed payment because its transaction_id {parsed_payment.transaction_id} is already in the database."
                            )
                        await payment_session.rollback()
                        skipped += 1
                        continue
                    imported += 1

                audit_logger.info(
                    f"Retrieved {imported} and skipped {skipped} payments."
                )
                cur_start_date = cur_end_date + timedelta(days=1)


async def get_gocardless_payments(
    requisition_id: int | None = None,
    date_from: datetime = datetime.today() - timedelta(days=7),
):
    processed_accounts: set[str] = set()

    async with async_session_maker() as session:
        if requisition_id is not None:
            requisition_q = await session.execute(
                select(ent.Requisition)
                .options(
                    selectinload(ent.Requisition.user),
                )
                .where(
                    and_(
                        ent.Requisition.id == requisition_id,
                        not_(ent.Requisition.status.in_(EXCLUDED_STATUSES)),
                    )
                )
            )
            requisition = requisition_q.scalars().first()
            if not requisition:
                raise ValueError("No valid Requisition found")
            requisitions: Sequence = [requisition]
        elif requisition_id is None:
            requisition_q = await session.execute(
                select(ent.Requisition)
                .options(selectinload(ent.Requisition.user))
                .where(not_(ent.Requisition.status.in_(EXCLUDED_STATUSES)))
            )
            requisitions = requisition_q.scalars().all()
        else:
            raise ValueError()

        for i in requisitions:
            await process_requisition(session, i, date_from, processed_accounts)
