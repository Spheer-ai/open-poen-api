from .. import models as ent
from sqlalchemy import select, and_, inspect, not_
from sqlalchemy.ext.asyncio import AsyncSession
from .utils import client
from datetime import datetime, timedelta
from collections.abc import MutableMapping
from dateutil.parser import parse
import re
from decimal import Decimal
from sqlalchemy.orm import selectinload
from asyncio import sleep
from ..database import async_session_maker


CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")
ALLOWED_PAYMENT_FIELDS = [f.key for f in inspect(ent.Payment).attrs]
# Retrieve payments in chunks of N days.
PAYMENT_RETRIEVAL_INTERVAL = 14
# Don't process requisitions with these statuses. Requisitions with
# statuses will never again become valid for payment retrieval.
EXCLUDED_STATUSES = [
    ent.ReqStatus.SUSPENDED,
    ent.ReqStatus.EXPIRED,
    ent.ReqStatus.CONFLICTED,
]


def _flatten(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(_flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


async def process_requisition(
    session: AsyncSession,
    requisition: ent.Requisition,
    date_from: datetime,
    processed_accounts: set[str],
):
    api_requisition = client.requisition.get_requisition_by_id(
        requisition.api_requisition_id
    )
    await sleep(1)

    requisition.status = ent.ReqStatus(api_requisition["status"])
    session.add(requisition)
    await session.commit()

    if not requisition.status == ent.ReqStatus.LINKED:
        return

    for account in api_requisition["accounts"]:
        # TODO: Make sure we don't do double imports for an account.
        # (Multiple requisitions can be for the same account.)
        if account in processed_accounts:
            continue
        else:
            processed_accounts.add(account)

        api_account = client.account_api(account)
        metadata = api_account.get_metadata()
        await sleep(1)

        if metadata["status"] != "READY":
            continue

        details = api_account.get_details()
        await sleep(1)

        account_q = await session.execute(
            select(ent.BankAccount)
            .where(ent.BankAccount.api_account_id == metadata["id"])
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
        if not account:
            account = ent.BankAccount(
                api_account_id=metadata["id"],
                iban=metadata["iban"],
                name=details["account"]["name"],
                created=parse(metadata["created"]),
                last_accessed=parse(metadata["last_accessed"]),
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
                session.add(requisition)
                await session.commit()
            if requisition not in account.requisitions:
                account.requisitions.append(requisition)
            account.last_accessed = parse(metadata["last_accessed"])
            session.add(account)
            await session.commit()

        date_to = datetime.now()
        cur_start_date = date_from
        while cur_start_date < date_to:
            cur_end_date = min(
                cur_start_date + timedelta(days=PAYMENT_RETRIEVAL_INTERVAL), date_to
            )
            api_transactions = api_account.get_transactions(
                date_from=cur_start_date.strftime("%Y-%m-%d"),
                date_to=cur_end_date.strftime("%Y-%m-%d"),
            )
            await sleep(1)
            for payment in api_transactions["transactions"]["booked"]:
                payment = {
                    CAMEL_CASE_PATTERN.sub("_", k).lower(): v
                    for (k, v) in payment.items()
                }
                payment["booking_date"] = parse(payment["booking_date"])
                payment["transaction_amount"] = Decimal(
                    payment["transaction_amount"]["amount"]
                )
                route = (
                    ent.Route.INCOME
                    if payment["transaction_amount"] > 0
                    else ent.Route.EXPENSES
                )
                payment = {k: (v if v != "" else None) for (k, v) in payment.items()}
                payment_db_q = await session.execute(
                    select(ent.Payment).where(
                        ent.Payment.transaction_id == payment["transaction_id"]
                    )
                )
                if payment_db_q.scalars().first():
                    continue

                if (
                    "creditor_account" in payment.keys()
                    and payment["creditor_account"] is not None
                ):
                    payment["creditor_account"] = payment["creditor_account"]["iban"]
                if (
                    "debtor_account" in payment.keys()
                    and payment["debtor_account"] is not None
                ):
                    payment["debtor_account"] = payment["debtor_account"]["iban"]

                new_payment = ent.Payment(
                    **{k: v for k, v in payment.items() if k in ALLOWED_PAYMENT_FIELDS},
                    route=route,
                    type=ent.PaymentType.GOCARDLESS,
                    bank_account_id=account.id
                )
                session.add(new_payment)
                await session.commit()

            cur_start_date = cur_end_date


async def get_gocardless_payments(
    requisition_id: int | None = None,
    date_from: datetime = datetime.today() - timedelta(days=7),
):
    async with async_session_maker() as session:
        processed_accounts: set[str] = set()

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
            await process_requisition(
                session, requisition, date_from, processed_accounts
            )
        else:
            requisition_q_list = (
                select(ent.Requisition)
                .options(selectinload(ent.Requisition.user))
                .where(not_(ent.Requisition.status.in_(EXCLUDED_STATUSES)))
                .execution_options(yield_per=256)
            )
            for requisition in await session.scalars(requisition_q_list):
                await process_requisition(
                    session, requisition, date_from, processed_accounts
                )
