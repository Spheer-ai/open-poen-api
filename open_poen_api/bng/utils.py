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


def _flatten(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(_flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _parse_and_save_payments(payments):
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    new_payments = []

    for payment in payments:
        # Flatten the nested dictionary. Otherwise we won't be able to save it in the database.
        payment = _flatten(payment)
        # Convert from camel case to snake case to match the column names in the database.
        payment = {pattern.sub("_", k).lower(): v for (k, v) in payment.items()}
        # These two fields need to be cast. The other fields are strings and should remain so.
        payment["booking_date"] = parse(payment["booking_date"])
        # To prevent importing a transaction that is not definitive yet.
        diff = datetime.today() - payment["booking_date"]
        if diff.days < 1:
            continue
        payment["transaction_amount"] = float(payment["transaction_amount"])
        if payment["transaction_amount"] > 0:
            route = "inkomsten"
        else:
            route = "uitgaven"
        # Get the card number, if one was used. This is used to identify what payments where done for
        # what project later on. These numbers always start with 6731924.
        try:
            card_number = re.search(
                "6731924\d*", payment["remittance_information_unstructured"]
            ).group(0)
        except AttributeError:
            card_number = None
        # To simplify things, we always save empty strings as None (NULL).
        payment = {k: (v if v != "" else None) for (k, v) in payment.items()}
        new_payments.append(
            Payment(
                **payment,
                route=route,
                card_number=card_number,
                type="BNG",
            )
        )

    # This is done to ensure we don't save the same transaction twice.
    existing_ids = set([x.transaction_id for x in Payment.query.all()])
    new_payments = [x for x in new_payments if x.transaction_id not in existing_ids]

    # Because we need to save new card numbers before new payments. This has to do
    # with the fact that card_number is a foreign key in the payment table.
    existing_card_numbers = [x.card_number for x in DebitCard.query.all()]
    new_card_numbers = set(
        [
            x.card_number
            for x in new_payments
            if x.card_number not in existing_card_numbers and x.card_number is not None
        ]
    )

    try:
        db.session.bulk_save_objects(
            [DebitCard(card_number=x) for x in new_card_numbers]
        )
        db.session.commit()
    except (ValueError, IntegrityError):
        db.session.rollback()
        raise

    try:
        db.session.bulk_save_objects(new_payments)
        db.session.commit()
    except (ValueError, IntegrityError):
        db.session.rollback()
        raise


def get_bng_payments():
    bng_account = BNGAccount.query.all()
    if len(bng_account) > 1:
        raise NotImplementedError(
            "Op dit moment ondersteunen we slechts één BNG-koppeling."
        )
    if len(bng_account) == 0:
        return
    bng_account = bng_account[0]

    account_info = read_account_information(
        bng_account.consent_id, bng_account.access_token
    )
    if len(account_info["accounts"]) > 1:
        raise NotImplementedError(
            "Op dit moment ondersteunen we slechts één consent per BNG-koppeling."
        )
    elif len(account_info["accounts"]) == 0:
        raise TypeError(
            "Het zou niet mogelijk moeten zijn om wel een account te hebben, maar geen consent."
        )

    date_from = datetime.today() - timedelta(days=365)

    # TODO: Make this part asynchronous?
    # TODO: What to do with booking status? Are we interested in pending?
    # TODO: What about balance?

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

    _parse_and_save_payments(payments)

    # We save it as a naive datetime object, but in the right timezone, to avoid having to use timezones
    # in Postgres.
    bng_account.last_import_on = datetime.now(
        pytz.timezone("Europe/Amsterdam")
    ).replace(tzinfo=None)
    db.session.add(bng_account)
    db.session.commit()
