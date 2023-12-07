from open_poen_api import database as db
from open_poen_api.app import app
from open_poen_api.models import (
    Base,
    RegulationRole,
    Payment,
    DebitCard,
    Requisition,
    BankAccount,
    UserBankAccountRole,
    BankAccountRole,
)
from open_poen_api.managers import superuser, required_login, optional_login
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pytest_asyncio
import base64
import urllib.parse
from open_poen_api.database import get_user_db
import open_poen_api.managers as m
from open_poen_api.schemas import (
    UserCreateWithPassword,
    InitiativeCreate,
    ActivityCreate,
    FunderCreate,
    RegulationCreate,
    GrantCreate,
    PaymentCreateAll,
)
import json
from dateutil.parser import isoparse
from io import BytesIO
from fastapi import UploadFile
import asyncio
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.event import listens_for


bankaccount_owner = 1
superuser = 6
userowner = 1
user = 7
admin = 5
grant_officer = 11
initiative_owner = 12
activity_owner = 13
anon = None

initiative_info = {
    "name": "Piets Buurtbarbeque",
    "description": "Piet wordt vijftig.",
    "purpose": "Saamhorigheid in de buurt bevorderen.",
    "target_audience": "Mensen uit buurt De Florijn.",
    "owner": "Mark de Wijk",
    "owner_email": "markdewijk@spheer.ai",
    "legal_entity": "stichting",
    "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
    "kvk_registration": "12345678",
    "location": "Amsterdam",
    "budget": 1000.00,
}

activity_info = {
    "name": "Zomer Picnic",
    "description": "Een fantastische picnic in het park.",
    "purpose": "Bevorderen buurtgevoel.",
    "target_audience": "Mensen uit buurt De Florijn",
    "budget": 100.00,
}

funder_info = {
    "name": "Gemeente Amsterdam",
    "url": "https://amsterdam.nl",
}

regulation_info = {
    "name": "Regeling Buurtcohesie",
    "description": "Voor het bevorderen van sociale cohesie in de buurt.",
}

grant_info = {
    "name": "Beschikking BBQ",
    "reference": "AB1234",
    "budget": 1000.01,
}


async def hide_instance(dummy_session, cls, id):
    i = await dummy_session.get(cls, id)
    i.hidden = True
    dummy_session.add(i)
    await dummy_session.commit()


def load_json(json_file_path):
    with open(json_file_path, "r") as file:
        data = json.load(file)
    return data


async def retrieve_token_from_last_sent_email():
    """Gets the last send email from Mailhog, assumes it's an email reply to a password
    reset request and parses the token inside it to return it."""
    async with AsyncClient() as client:
        response = await client.get("http://mail:8025/api/v2/messages")
        if response.status_code == 200:
            emails = response.json()["items"]
            if len(emails) > 0:
                response = await client.get(
                    f"http://mail:8025/api/v1/messages/{emails[0]['ID']}"
                )
                text = base64.b64decode(
                    response.json()["MIME"]["Parts"][0]["Body"]
                ).decode("utf-8")
                lines = text.split("\n")
                try:
                    url = next(line for line in lines if "reset-password" in line)
                except StopIteration:
                    raise ValueError("No reset-password found.")
                pattern = r"\?token=(.*)"
                token_match = re.search(pattern, url)
                if token_match:
                    return token_match.group(1)
                else:
                    raise ValueError("Token not found in the URL.")
            else:
                raise ValueError("No emails present.")
        else:
            raise ValueError("Request to Mailhog failed.")


@pytest_asyncio.fixture
async def async_client(overridden_app):
    async with AsyncClient(
        app=overridden_app, base_url="http://localhost:8000"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def clean_async_client():
    async with AsyncClient(app=app, base_url="http://localhost:8000") as client:
        yield client


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_session():
    # Clear and reset the db.
    async with db.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Add dummy data.
    async with db.async_session_maker() as s:
        s = await add_dummy_data(s)

    yield

    # Clear the entire db.
    async with db.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose of the engine.
    await db.async_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def dummy_session(async_session):
    # https://www.core27.co/post/transactional-unit-tests-with-pytest-and-async-sqlalchemy

    connection = await db.async_engine.connect()
    trans = await connection.begin()
    async with db.async_session_maker(bind=connection) as s:
        nested = await connection.begin_nested()

        @listens_for(s.sync_session, "after_transaction_end")
        def end_savepoint(session, transaction):
            nonlocal nested

            if not nested.is_active:
                nested = connection.sync_connection.begin_nested()

        yield s

    await trans.rollback()
    await connection.close()


async def add_dummy_data(async_session):
    db = await get_user_db(async_session).__anext__()
    user_manager = m.UserManager(db, async_session, None)
    initiative_manager = m.InitiativeManager(async_session, None)
    activity_manager = m.ActivityManager(async_session, None)
    funder_manager = m.FunderManager(async_session, None)
    regulation_manager = m.RegulationManager(async_session, None)
    grant_manager = m.GrantManager(async_session, None)
    bank_account_manager = m.BankAccountManager(async_session, None)
    payment_manager = m.PaymentManager(async_session, None)

    users = load_json("./tests/dummy_data/users.json")
    for user in users:
        schema = UserCreateWithPassword(**user)
        await user_manager.create(schema, request=None)
    funders = load_json("./tests/dummy_data/funders.json")
    for funder in funders:
        schema = FunderCreate(**funder)
        await funder_manager.create(schema, request=None)
    regulations = load_json("./tests/dummy_data/regulations.json")
    for regulation in regulations:
        funder_id = regulation.pop("funder_id")
        schema = RegulationCreate(**regulation)
        await regulation_manager.create(schema, funder_id, request=None)
    grants = load_json("./tests/dummy_data/grants.json")
    for grant in grants:
        regulation_id = grant.pop("regulation_id")
        schema = GrantCreate(**grant)
        await grant_manager.create(schema, regulation_id, request=None)
    initiatives = load_json("./tests/dummy_data/initiatives.json")
    for init in initiatives:
        grant_id = init.pop("grant_id")
        schema = InitiativeCreate(**init)
        await initiative_manager.create(schema, grant_id, request=None)
    activities = load_json("./tests/dummy_data/activities.json")
    for act in activities:
        initiative_id = act.pop("initiative_id")
        schema = ActivityCreate(**act)
        await activity_manager.create(schema, initiative_id, request=None)
    requisitions = load_json("./tests/dummy_data/requisitions.json")
    for r in requisitions:
        requisition = Requisition(**r)
        async_session.add(requisition)
        await async_session.commit()
    bank_accounts = load_json("./tests/dummy_data/bank_accounts.json")
    for ba in bank_accounts:
        requisition_ids = ba.pop("requisition_ids")
        ba["created"] = isoparse(ba["created"])
        ba["last_accessed"] = isoparse(ba["last_accessed"])
        requisitions_q = await async_session.execute(
            select(Requisition).where(Requisition.id.in_(requisition_ids))
        )
        requisitions = requisitions_q.scalars().all()
        bank_account = BankAccount(**ba)
        bank_account.requisitions = requisitions
        async_session.add(bank_account)
        await async_session.commit()
    debit_cards = load_json("./tests/dummy_data/debit_cards.json")
    for dc in debit_cards:
        debit_card = DebitCard(**dc)
        async_session.add(debit_card)
        await async_session.commit()
    payments = load_json("./tests/dummy_data/payments.json")
    for p in payments:
        schema = PaymentCreateAll(**p)
        payment = Payment(**schema.dict())
        async_session.add(payment)
        await async_session.commit()

    # TODO: Fix magical constants.
    regulation = await regulation_manager.min_load(6)
    await regulation_manager.make_users_officer(
        regulation, user_ids=[11], regulation_role=RegulationRole.GRANT_OFFICER
    )

    initiative = await initiative_manager.min_load(1)
    await initiative_manager.make_users_owner(initiative, user_ids=[12])

    activity = await activity_manager.min_load(1)
    await activity_manager.make_users_owner(activity, user_ids=[13])

    bank_account_roles = [
        UserBankAccountRole(user_id=1, bank_account_id=1, role=BankAccountRole.OWNER),
        UserBankAccountRole(user_id=2, bank_account_id=2, role=BankAccountRole.OWNER),
    ]
    async_session.add_all(bank_account_roles)
    await async_session.commit()

    with open("tests/dummy_data/test.png", "rb") as f:
        image_content = f.read()

    mock_upload_file = UploadFile(
        filename="test.png",
        file=BytesIO(image_content),
        headers={"content-type": "image/png"},
    )
    user_db = await user_manager.detail_load(1)
    await user_manager.profile_picture_handler.set(
        mock_upload_file, user_db, request=None
    )
    mock_upload_file = UploadFile(
        filename="test.png",
        file=BytesIO(image_content),
        headers={"content-type": "image/png"},
    )
    payment_db = await payment_manager.detail_load(15)
    await payment_manager.attachment_handler.set(
        [mock_upload_file], payment_db, request=None
    )

    return async_session


@pytest_asyncio.fixture(scope="function")
async def get_mock_user(request, dummy_session):
    if request.param is None:
        return lambda: None

    db = await get_user_db(dummy_session).__anext__()
    user_manager = m.UserManager(db, dummy_session, None)
    user_instance = await user_manager.requesting_user_load(request.param)
    # This expunge is important to prevent the data on this user from being
    # manipulated and or erased after another instance is queried that shares
    # data with this user instance. SQL-Alchemy optimization it seems.
    # (This session is shared with the app itself.)
    dummy_session.expunge(user_instance)

    async def func():
        return user_instance

    return func


@pytest_asyncio.fixture(scope="function")
async def overridden_app(get_mock_user, dummy_session):
    app.dependency_overrides[superuser] = get_mock_user
    app.dependency_overrides[required_login] = get_mock_user
    app.dependency_overrides[optional_login] = get_mock_user
    app.dependency_overrides[db.get_async_session] = lambda: dummy_session
    yield app
    app.dependency_overrides = {}
