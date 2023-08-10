from open_poen_api.database import (
    async_session_maker,
    asyng_engine,
)
from open_poen_api.app import app
from open_poen_api.models import Base, User, Initiative, UserRole, Activity
from open_poen_api.routes import superuser_dep, required_login_dep, optional_login_dep
from open_poen_api.managers import user_manager as um
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
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
)
import json


superuser_info = {
    "obj_id": 42,
    "role": UserRole.USER,
    "email": "test@example.com",
    "is_active": True,
    "is_superuser": True,
    "is_verified": True,
    "return_none": False,
}
userowner_info = superuser_info.copy()
userowner_info.update({"obj_id": 1})
userowner_info.update({"is_superuser": False})
user_info = userowner_info.copy()
user_info.update({"obj_id": 42})
admin_info = user_info.copy()
admin_info.update({"role": "administrator"})
anon_info = user_info.copy()
anon_info.update({"return_none": True})

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


async def retrieve_token_from_last_sent_email():
    """Gets the last send email from Mailhog, assumes it's an email reply to a password
    reset request and parses the token inside it to return it."""
    async with AsyncClient() as client:
        response = await client.get("http://localhost:8025/api/v2/messages")
        if response.status_code == 200:
            emails = response.json()["items"]
            if len(emails) > 0:
                response = await client.get(
                    f"http://localhost:8025/api/v1/messages/{emails[0]['ID']}"
                )
                text = base64.b64decode(
                    response.json()["MIME"]["Parts"][0]["Body"]
                ).decode("utf-8")
                lines = text.split("\n")
                try:
                    url = next(line for line in lines if "reset-password" in line)
                except StopIteration:
                    raise ValueError("No reset-password found.")
                path = urllib.parse.urlparse(url).path
                _, token = path.split("/reset-password/")
                return token
            else:
                raise ValueError("No emails present.")
        else:
            raise ValueError("Request to Mailhog failed.")


@pytest_asyncio.fixture
async def get_mock_user(request):
    user_info = request.param
    if user_info["return_none"]:
        val = None
    else:
        val = User(
            id=user_info["obj_id"],
            role=user_info["role"],
            email=user_info["email"],
            is_active=user_info["is_active"],
            is_superuser=user_info["is_superuser"],
            is_verified=user_info["is_verified"],
        )

    async def func():
        return val

    return func


@pytest_asyncio.fixture
async def overridden_app(get_mock_user):
    app.dependency_overrides[superuser_dep] = get_mock_user
    app.dependency_overrides[required_login_dep] = get_mock_user
    app.dependency_overrides[optional_login_dep] = get_mock_user
    yield app
    app.dependency_overrides = {}


@pytest_asyncio.fixture
async def async_client(event_loop, overridden_app):
    async with AsyncClient(
        app=overridden_app, base_url="http://localhost:8000"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def clean_async_client(event_loop):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def async_session(event_loop) -> AsyncSession:
    async with async_session_maker() as s:
        async with asyng_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        yield s

    async with asyng_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await asyng_engine.dispose()


def load_json(json_file_path):
    with open(json_file_path, "r") as file:
        data = json.load(file)
    return data


@pytest_asyncio.fixture(scope="function")
async def dummy_session(async_session):
    db = await get_user_db(async_session).__anext__()
    user_manager = await m.get_user_manager(db).__anext__()
    initiative_manager = await m.get_initiative_manager(async_session).__anext__()
    activity_manager = await m.get_activity_manager(async_session).__anext__()
    funder_manager = await m.get_funder_manager(async_session).__anext__()
    regulation_manager = await m.get_regulation_manager(async_session).__anext__()
    grant_manager = await m.get_grant_manager(async_session).__anext__()
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
    return async_session


@pytest_asyncio.fixture(scope="function")
async def as_1(async_session):
    # One user.
    db = await m.get_user_db(async_session).__anext__()
    um = await m.get_user_manager(db).__anext__()
    s = UserCreateWithPassword(
        email="existing@user.com", role="user", password="testing"
    )
    u = await um.create(s, request=None)
    return async_session


@pytest_asyncio.fixture(scope="function")
async def as_2(as_1):
    # One initiative and one user.
    im = await m.get_initiative_manager(as_1).__anext__()
    for i in (1, 2, 3):
        info = initiative_info.copy()
        if i > 1:
            info.update({"name": info["name"] + str(i)})
        s = InitiativeCreate(**info)
        i = await im.create(s, request=None)
    return as_1


@pytest_asyncio.fixture(scope="function")
async def as_3(as_2):
    # One initiative and one user linked to one another.
    im = await m.get_initiative_manager(as_2).__anext__()
    i = await im.detail_load(1)
    i = await im.make_users_owner(i, [1], request=None)
    return as_2


@pytest_asyncio.fixture(scope="function")
async def as_4(as_3):
    # One initiative + activity and one user linked to one another.
    am = await m.get_activity_manager(as_3).__anext__()
    s = ActivityCreate(**activity_info)
    a = await am.create(s, 1, request=None)
    return as_3


@pytest_asyncio.fixture(scope="function")
async def as_5(as_4):
    # One initiative + activity + user and three users that are linked
    # to the activity.
    db = await m.get_user_db(as_4).__anext__()
    um = await m.get_user_manager(db).__anext__()
    am = await m.get_activity_manager(as_4).__anext__()
    a = await as_4.get(Activity, 1)
    ids = []
    for i in (1, 2, 3):
        s = UserCreateWithPassword(
            email=f"extra{i}@user.com", role="user", password="testing"
        )
        u = await um.create(s, request=None)
        ids.append(u.id)
    await am.make_users_owner(a, ids, request=None)
    return as_4
