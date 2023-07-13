from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import os
import collections
import re
from tempfile import TemporaryDirectory
import zipfile
import json
from dateutil.parser import parse
import pytz
from fastapi import Request
from .api import read_account_information, read_transaction_list
from ..schemas_and_models.models import entities as ent
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from sqlalchemy import select


CAMEL_CASE_PATTERN = re.compile(r"(?<!^)(?=[A-Z])")


def _flatten(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(_flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _parse_and_save_payments(session: AsyncSession, payments):
    for payment in payments:
        # Flatten the nested dictionary. Otherwise we won't be able to save it in the database.
        payment = _flatten(payment)
        # Convert from camel case to snake case to match the column names in the database.
        payment = {
            CAMEL_CASE_PATTERN.sub("_", k).lower(): v for (k, v) in payment.items()
        }
        payment["booking_date"] = parse(payment["booking_date"])
        # Transactions are only definitive past one day after entry.
        diff = datetime.today() - payment["booking_date"]
        if diff.days < 1:
            continue
        payment["transaction_amount"] = Decimal(payment["transaction_amount"])
        if payment["transaction_amount"] > 0:
            route = "inkomsten"
        else:
            route = "uitgaven"
        # Parse the debit card, if any, in the payment information field.
        found = re.search("6731924\d*", payment["remittance_information_unstructured"])
        card_number = found.group(0) if found is not None else None
        # Ensure we save empty strings as NULL.
        payment = {k: (v if v != "" else None) for (k, v) in payment.items()}

        if card_number is None:
            card_id = None
        elif (
            debit_card := session.exec(
                select(ent.DebitCard).where(ent.DebitCard.card_number == card_number)
            ).first()
        ) is not None:
            card_id = debit_card.id
        else:
            debit_card = ent.DebitCard(card_number=card_number)
            session.add(debit_card)
            session.commit()
            session.refresh(debit_card)
            card_id = debit_card.id

        payment = ent.Payment(**payment, route=route, type="BNG", debit_card_id=card_id)
        try:
            session.add(payment)
            session.commit()
        except IntegrityError:
            session.rollback()


def get_bng_payments(
    session: AsyncSession, date_from: datetime = datetime.today() - timedelta(days=31)
):
    bng_account = session.exec(select(ent.BNG)).first()
    if not bng_account:
        # TODO: Log.
        return

    account_info = read_account_information(
        bng_account.consent_id, bng_account.access_token
    )
    if not len(account_info["accounts"]) == 1:
        raise ValueError("There are either multiple accounts, or none.")

    transaction_list = read_transaction_list(
        bng_account.consent_id,
        bng_account.access_token,
        account_info["accounts"][0]["resourceId"],
        date_from.strftime("%Y-%m-%d"),
    )

    with TemporaryDirectory() as d:
        with open(os.path.join(d, "transaction_list.zip"), "wb") as f:
            f.write(transaction_list)
        with zipfile.ZipFile(os.path.join(d, "transaction_list.zip")) as z:
            z.extractall(d)
        payment_json_files = [x for x in os.listdir(d) if x.endswith(".json")]
        if len(payment_json_files) != 1:
            raise TypeError(
                "The downloaded transaction zip does not contain a json file."
            )
        with open(os.path.join(d, payment_json_files[0])) as f:
            payments = json.load(f)
            payments = payments["transactions"]["booked"]

    _parse_and_save_payments(session, payments)

    bng_account.last_import_on = datetime.now(pytz.timezone("Europe/Amsterdam"))
    session.add(bng_account)
    session.commit()
