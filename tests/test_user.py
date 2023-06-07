import pytest
from fastapi.testclient import TestClient
from open_poen_api.app import app


client = TestClient(app)


def test_create_user():
    user_data = {
        "email": "johndoe@gmail.com",
    }

    response = client.post("/user", json=user_data)

    assert response.status_code == 200
    password = response.json()["plain_password"]


def test_retrieve_token():
    data = {"username": "johndoe@gmail.com", "password": password}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, json=data)
    assert response.status_code == 200
