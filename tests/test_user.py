from open_poen_api.app import app
from open_poen_api.database import get_session
import open_poen_api.models as m
from .fixtures import client, created_user


def test_create_user(created_user):
    assert created_user["id"] == 1
    assert created_user["email"] == "johndoe@gmail.com"


def test_duplicate_email(client, created_user):
    # We create johndoe@gmail.com for the second time by
    # having user_password as a fixture here.
    user_data = {
        "email": "johndoe@gmail.com",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email address already registered"


def test_create_and_delete_user(client):
    user_data = {
        "email": "janedoe@gmail.com",
        "role": "financial",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    assert response.json()["role"] == "financial"

    user_id = response.json()["id"]
    delete_response = client.delete(f"/user/{user_id}")
    assert delete_response.status_code == 204


def test_delete_non_existing_user(client):
    response = client.delete("/user/42")
    assert response.status_code == 404


def test_update_user(client, created_user):
    user_data = {
        "id": created_user["id"],
        "first_name": "John",
        "last_name": "Doe",
        "email": created_user["email"],
    }
    response = client.put(f"/user/{user_data['id']}", json=user_data)
    assert response.status_code == 200
    s = next(get_session())
    user = s.get(m.User, created_user["id"])
    assert user.first_name == "John"
    assert user.last_name == "Doe"
    assert user.role == "user"
    s.close()


def test_get_users(client, created_user):
    response = client.get("/users")
    assert response.status_code == 200
    s = next(get_session())
    user = s.get(m.User, created_user["id"])

    def check_user_fields(user, user_dict):
        for field, value in user_dict.items():
            if getattr(user, field) != value:
                return False
        return True

    assert check_user_fields(user, response.json()["users"][0])


def test_retrieve_token(client, created_user):
    data = {"username": "johndoe@gmail.com", "password": "DEBUG_PASSWORD"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )


def test_add_non_existing_initiative(client):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [42],
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "One or more initiatves do not exist"
    return response.json()
