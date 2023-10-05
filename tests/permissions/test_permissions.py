from open_poen_api.authorization.authorization import (
    OSO,
    get_authorized_output_fields,
    set_sqlalchemy_adapter,
    get_authorized_actions,
)
from open_poen_api.database import sync_session_maker
from open_poen_api.models import User, Regulation
from open_poen_api.managers import RegulationManager
import pytest_asyncio
import pytest
from oso.exceptions import NotFoundError, ForbiddenError
from tests.conftest import superuser, user, userowner


@pytest_asyncio.fixture(scope="function")
async def user_data(async_session):
    superuser = User(
        hashed_password="123456",
        email="superuser@gmail.com",
        is_superuser=True,
        role="user",
    )
    financial = User(hashed_password="123456", email="financial@gmail.com", role="financial")
    administrator = User(
        hashed_password="123456", email="administrator@gmail.com", role="administrator"
    )
    user = User(hashed_password="123456", email="user@gmail.com", role="user")
    async_session.add_all([superuser, financial, administrator, user])
    await async_session.commit()
    for i in (superuser, financial, administrator, user):
        await async_session.refresh(i)
    return {
        "superuser": superuser,
        "financial": financial,
        "administrator": administrator,
        "user": user,
    }


action_combs = [
    ("superuser", "read", "user", True),
    ("superuser", "edit", "user", True),
    ("superuser", "delete", "user", True),
    ("superuser", "delete", "superuser", False),
    ("user", "edit", "user", True),
    ("user", "edit", "financial", False),
    ("user", "delete", "user", False),
    ("user", "delete", "administrator", False),
    ("financial", "edit", "financial", True),
    ("financial", "read", "user", True),
]


@pytest.mark.parametrize("actor,action,resource,allowed", action_combs)
async def test_action_permissions(actor, action, resource, allowed, user_data):
    actor = user_data[actor]
    resource = user_data[resource]
    if not allowed:
        with pytest.raises((NotFoundError, ForbiddenError)):
            OSO.authorize(actor, action, resource)
    else:
        OSO.authorize(actor, action, resource)


field_combs = [
    ("superuser", "read", "user", ["id", "first_name", "last_name", "email"], True),
    ("user", "read", "user", ["id", "first_name", "last_name", "email"], True),
    ("financial", "read", "user", ["id", "first_name", "last_name", "email"], False),
    ("financial", "read", "user", ["id", "first_name"], True),
]


@pytest.mark.parametrize("actor,action,resource,fields,are_authorized", field_combs)
async def test_field_permissions(actor, action, resource, fields, are_authorized, user_data):
    actor = user_data[actor]
    resource = user_data[resource]
    authorized_fields = OSO.authorized_fields(actor, "read", resource)
    all_fields_are_authorized = all([i in authorized_fields for i in fields])
    if are_authorized:
        assert all_fields_are_authorized
    else:
        assert not all_fields_are_authorized


async def test_get_authorized_output_fields(dummy_session):
    user = await dummy_session.get(User, 1)
    regulation = await dummy_session.get(Regulation, 1)
    fields = get_authorized_output_fields(user, "read", regulation, OSO)


async def test_get_authorized_output_fields_2(dummy_session):
    regulation_manager = RegulationManager(dummy_session, None)
    with sync_session_maker() as s:
        oso = await set_sqlalchemy_adapter(s).__anext__()
        user = await dummy_session.get(User, 1)
        regulation = await regulation_manager.detail_load(1)
        fields = get_authorized_output_fields(user, "read", regulation, oso)


async def test_get_authorized_actions(dummy_session):
    actor = await dummy_session.get(User, 1)
    user1 = await dummy_session.get(User, 1)
    user2 = await dummy_session.get(User, 2)
    actions1 = get_authorized_actions(actor, user1, OSO)
    actions2 = get_authorized_actions(actor, user2, OSO)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, entity_class, entity_id, status_code, actions",
    [
        (superuser, "User", user, 200, {"edit", "delete", "create", "read"}),
        (user, "User", superuser, 200, {"read"}),
        (userowner, "User", userowner, 200, {"read", "edit"}),
    ],
    ids=["Superuser has all", "User has only read", "Userowner has read and delete"],
    indirect=["get_mock_user"],
)
async def test_get_authorized_actions_2(
    async_client, dummy_session, entity_class, entity_id, status_code, actions
):
    url = f"/auth/entity-access/actions?entity_class={entity_class}&"
    if entity_id is not None:
        url += f"entity_id={entity_id}&"

    response = await async_client.get(url[:-1])
    assert response.status_code == status_code
    if status_code == 200:
        assert set(response.json()["actions"]) == actions
