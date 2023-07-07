import pytest
from open_poen_api.schemas_and_models.models.entities import User
from tests.conftest import retrieve_token_from_last_sent_email
import asyncio


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
async def test_first_login(async_client, async_session, existing_user):
    body = {"email": existing_user["email"]}
    response = await async_client.post("/auth/forgot-password", json=body)
    assert response.status_code == 202
    # Give FastAPI to send the mail as a background task.
    await asyncio.sleep(1)
    token = await retrieve_token_from_last_sent_email()
    body = {"token": token, "password": "SomeNewPassword"}
    response = await async_client.post("/auth/reset-password", json=body)
    assert response.status_code == 200
    body = {"username": existing_user["email"], "password": "SomeNewPassword"}
    response = await async_client.post(
        "/auth/jwt/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json().keys()
