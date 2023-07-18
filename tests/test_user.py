import pytest
from open_poen_api.schemas_and_models.models.entities import User
from tests.conftest import retrieve_token_from_last_sent_email
import asyncio
from open_poen_api.app import app
import open_poen_api.user_manager as auth


superuser_info = {
    "obj_id": 1,
    "role": "user",
    "email": "test@example.com",
    "is_active": True,
    "is_superuser": True,
    "is_verified": True,
    "return_none": False,
}
userowner_info = superuser_info.copy()
userowner_info.update({"is_superuser": False})
user_info = userowner_info.copy()
user_info.update({"obj_id": 42})


@pytest.mark.asyncio
async def test_create_user(async_client, async_session):
    body = {"email": "test@example.com"}
    response = await async_client.post("/user", json=body)
    assert response.status_code == 200
    db_user = await async_session.get(User, response.json()["id"])
    assert db_user is not None
    user_data = response.json()
    assert user_data["email"] == body["email"]


@pytest.mark.asyncio
async def test_first_login(async_client, async_session, user_created_by_admin):
    body = {"email": user_created_by_admin["email"]}
    response = await async_client.post("/auth/forgot-password", json=body)
    assert response.status_code == 202
    # Give FastAPI to send the mail as a background task.
    await asyncio.sleep(1)
    token = await retrieve_token_from_last_sent_email()
    body = {"token": token, "password": "SomeNewPassword"}
    response = await async_client.post("/auth/reset-password", json=body)
    assert response.status_code == 200
    body = {"username": user_created_by_admin["email"], "password": "SomeNewPassword"}
    response = await async_client.post(
        "/auth/jwt/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json().keys()


@pytest.mark.asyncio
async def test_delete_user(async_client, async_session, user_created_by_admin):
    user_id = 1
    response = await async_client.delete(f"/user/{user_id}")
    assert response.status_code == 204
    user = await async_session.get(User, user_id)
    assert user is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "async_client, status_code",
    [(superuser_info, 200), (userowner_info, 200), (user_info, 403)],
    indirect=["async_client"],
)
async def test_patch_user(
    async_client, async_session, user_created_by_admin, status_code
):
    user_id = 1
    body = {"email": "different@user.com"}
    response = await async_client.patch(f"/user/{user_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        user = await async_session.get(User, user_id)
        assert user.email == "different@user.com"


@pytest.mark.asyncio
async def test_get_users(async_client, async_session, user_created_by_admin):
    response = await async_client.get("/users")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 1
