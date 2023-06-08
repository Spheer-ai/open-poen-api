import pytest
from fastapi.testclient import TestClient
from open_poen_api.app import app
from open_poen_api.database import get_session
import open_poen_api.models as m


client = TestClient(app)


@pytest.fixture(scope="module")
def created_user():
    user_data = {
        "email": "johndoe@gmail.com",
    }

    response = client.post("/user", json=user_data)
    try:
        r = response.json()
        parsed_response = {k: r[k] for k in ["plain_password", "id", "email"]}
    except:
        parsed_response = None
    return parsed_response


def test_create_user(created_user):
    assert created_user is not None


def test_duplicate_email(created_user):
    # We create johndoe@gmail.com for the second time by
    # having user_password as a fixture here.
    user_data = {
        "email": "johndoe@gmail.com",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email address already registered"


def test_create_and_delete_user():
    user_data = {
        "email": "janedoe@gmail.com",
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 200

    user_id = response.json()["id"]

    delete_response = client.delete(f"/user/{user_id}")
    assert delete_response.status_code == 204


def test_delete_non_existing_user():
    response = client.delete("/user/42")
    assert response.status_code == 404


def test_update_user(created_user):
    user_data = {
        "id": created_user["id"],
        "first_name": "John",
        "last_name": "Doe",
        "email": created_user["email"],
    }
    response = client.put(f"/user/{user_data['id']}", json=user_data)
    assert response.status_code == 200
    assert response.json() == user_data
    s = next(get_session())
    user = s.get(m.User, created_user["id"])
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    s.close()


def test_get_users(created_user):
    response = client.get("/users")
    assert response.status_code == 200
    user_data = {
        "id": created_user["id"],
        "first_name": None,
        "last_name": None,
        "email": created_user["email"],
    }
    assert response.json() == [user_data]


def test_retrieve_token(created_user):
    data = {"username": "johndoe@gmail.com", "password": created_user["plain_password"]}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )
