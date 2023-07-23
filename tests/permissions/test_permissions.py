from open_poen_api.authorization.authorization import OSO
from open_poen_api.schemas_and_models.models.entities import User
import pytest_asyncio
import pytest
from oso.exceptions import NotFoundError, ForbiddenError


@pytest_asyncio.fixture(scope="function")
async def user_data(async_session):
    superuser = User(
        hashed_password="123456",
        email="superuser@gmail.com",
        is_superuser=True,
        role="user",
    )
    financial = User(
        hashed_password="123456", email="financial@gmail.com", role="financial"
    )
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
async def test_field_permissions(
    actor, action, resource, fields, are_authorized, user_data
):
    actor = user_data[actor]
    resource = user_data[resource]
    authorized_fields = OSO.authorized_fields(actor, "read", resource)
    all_fields_are_authorized = all([i in authorized_fields for i in fields])
    if are_authorized:
        assert all_fields_are_authorized
    else:
        assert not all_fields_are_authorized
