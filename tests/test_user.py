import pytest
from open_poen_api.schemas_and_models.models.entities import User
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
        (userowner_info, {"email": "test@example.com"}, 403),
        (anon_info, {"email": "test@example.com"}, 403),
        (superuser_info, {"email": "existing@user.com"}, 400),
    ],
    indirect=["get_mock_user"],
)
async def test_create_user(async_client, as_1, body, status_code):
    response = await async_client.post("/user", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        db_user = await as_1.get(User, response.json()["id"])
        assert db_user is not None
        user_data = response.json()
        assert user_data["email"] == body["email"]


@pytest.mark.asyncio
async def test_first_login(clean_async_client, as_1):
    body = {"email": "existing@user.com"}
    response = await clean_async_client.post("/auth/forgot-password", json=body)
    assert response.status_code == 202
    # Give FastAPI to send the mail as a background task.
    await asyncio.sleep(1)
    token = await retrieve_token_from_last_sent_email()
    body = {"token": token, "password": "SomeNewPassword"}
    response = await clean_async_client.post("/auth/reset-password", json=body)
    assert response.status_code == 200
    body = {"username": "existing@user.com", "password": "SomeNewPassword"}
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
    indirect=["get_mock_user"],
)
async def test_delete_user(async_client, as_1, status_code):
    user_id = 1
    response = await async_client.delete(f"/user/{user_id}")
    assert response.status_code == status_code
    if status_code == 204:
        user = await as_1.get(User, user_id)
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
    indirect=["get_mock_user"],
)
async def test_patch_user(async_client, as_1, body, status_code):
    user_id = 1
    response = await async_client.patch(f"/user/{user_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        user = await as_1.get(User, user_id)
        for key in body:
            assert getattr(user, key) == body[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    indirect=["get_mock_user"],
)
async def test_get_users_list(async_client, as_1, status_code):
    response = await async_client.get("/users")
    assert response.status_code == status_code
    assert len(response.json()["users"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    indirect=["get_mock_user"],
)
async def test_get_user_detail(async_client, as_1, status_code):
    user_id = 1
    response = await async_client.get(f"/user/{user_id}")
    assert response.status_code == status_code
