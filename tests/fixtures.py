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
        "initiative_ids": [],
    }

    response = client.post("/user", json=user_data)
    try:
        r = response.json()
        parsed_response = {k: r[k] for k in ["plain_password", "id", "email"]}
    except:
        parsed_response = None
    return parsed_response
