import pytest
from open_poen_api.schemas_and_models.models.entities import User
from open_poen_api.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_create_user(client, clean_session):
    # Define the test data
    test_user = {"email": "test@example.com"}

    # Send the test request
    response = client.post("/user", json=test_user)

    # Assert that the response status code is 200
    assert response.status_code == 200

    # Fetch the created user from the database
    db_user = await clean_session.get(User, response.json()["id"])
    assert db_user is not None

    # Assert that the returned user matches the test data
    user_data = response.json()
    assert user_data["email"] == test_user["email"]
