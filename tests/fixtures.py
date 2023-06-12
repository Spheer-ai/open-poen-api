from fastapi.testclient import TestClient
from open_poen_api.app import app
import pytest


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def created_user(client):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    return response.json()
