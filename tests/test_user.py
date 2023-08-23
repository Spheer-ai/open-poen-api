import pytest
from open_poen_api.models import User
from tests.conftest import (
    retrieve_token_from_last_sent_email,
    superuser_info,
    userowner_info,
    user_info,
    anon_info,
)
import asyncio


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"email": "test@example.com"}, 200),
        (user_info, {"email": "test@example.com"}, 403),
        (anon_info, {"email": "test@example.com"}, 403),
        (superuser_info, {"email": "user1@example.com"}, 400),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Anon cannot",
        "Duplicate email fails",
    ],
    indirect=["get_mock_user"],
)
async def test_create_user(async_client, dummy_session, body, status_code):
    response = await async_client.post("/user", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        db_user = await dummy_session.get(User, response.json()["id"])
        assert db_user is not None
        user_data = response.json()
        assert user_data["email"] == body["email"]


@pytest.mark.asyncio
async def test_first_login(clean_async_client, dummy_session):
    body = {"email": "user1@example.com"}
    response = await clean_async_client.post("/auth/forgot-password", json=body)
    assert response.status_code == 202
    # Give FastAPI to send the mail as a background task.
    await asyncio.sleep(1)
    token = await retrieve_token_from_last_sent_email()
    body = {"token": token, "password": "SomeNewPassword123"}
    response = await clean_async_client.post("/auth/reset-password", json=body)
    assert response.status_code == 200
    body = {"username": "user1@example.com", "password": "SomeNewPassword123"}
    response = await clean_async_client.post(
        "/auth/jwt/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json().keys()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 204), (userowner_info, 403), (user_info, 403), (anon_info, 403)],
    ids=["Superuser can", "User owner cannot", "User cannot", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_delete_user(async_client, dummy_session, status_code):
    user_id = 1
    response = await async_client.delete(f"/user/{user_id}")
    assert response.status_code == status_code
    if status_code == 204:
        user = await dummy_session.get(User, user_id)
        assert user is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"email": "different@user.com"}, 200),
        (userowner_info, {"email": "different@user.com"}, 200),
        (user_info, {"email": "different@user.com"}, 403),
        (superuser_info, {"role": "financial"}, 200),
        (userowner_info, {"role": "financial"}, 403),
    ],
    ids=[
        "Superuser can change email",
        "User owner can change email",
        "User cannot change email",
        "Superuser can change role",
        "User owner cannot change role",
    ],
    indirect=["get_mock_user"],
)
async def test_patch_user(async_client, dummy_session, body, status_code):
    user_id = 1
    response = await async_client.patch(f"/user/{user_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        user = await dummy_session.get(User, user_id)
        for key in body:
            assert getattr(user, key) == body[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code, length",
    [(superuser_info, 200, 12), (user_info, 200, 11), (anon_info, 200, 11)],
    ids=["Superuser sees hidden", "User cannot see hidden", "Anon cannot see hidden"],
    indirect=["get_mock_user"],
)
async def test_get_users_list(async_client, dummy_session, status_code, length):
    response = await async_client.get("/users")
    assert response.status_code == status_code
    assert len(response.json()["users"]) == length


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code, fields_present, fields_not_present",
    [
        (superuser_info, 200, ["is_superuser", "hidden"], []),
        (userowner_info, 200, ["is_superuser", "hidden"], []),
        (anon_info, 200, ["first_name"], ["is_superuser", "hidden"]),
    ],
    ids=[
        "Superuser sees everything",
        "User owner sees everything",
        "Anon sees a little",
    ],
    indirect=["get_mock_user"],
)
async def test_get_user_detail(
    async_client, dummy_session, status_code, fields_present, fields_not_present
):
    user_id = 1
    response = await async_client.get(f"/user/{user_id}")
    assert response.status_code == status_code
    assert all([i in response.json() for i in fields_present])
    assert all([i not in response.json() for i in fields_not_present])
