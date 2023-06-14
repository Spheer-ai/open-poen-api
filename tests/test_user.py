from open_poen_api.app import app
from open_poen_api.database import get_session
import open_poen_api.models as m
from .conftest import client, session
from sqlmodel import select


def test_create_user(client, session):
    user_data = {
        "email": "janedoe@gmail.com",
        "role": "financial",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    assert "janedoe@gmail.com" in [i.email for i in session.exec(select(m.User)).all()]


def test_duplicate_email(client, session):
    user_data = {
        "email": "user1@example.com",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email address already registered"
    assert "user1@example" not in [i.email for i in session.exec(select(m.User)).all()]


def test_delete_non_existing_user(client, session):
    response = client.delete("/user/42")
    assert response.status_code == 404
    assert session.get(m.User, 44) is None


def test_update_user(client, session):
    existing_user = session.exec(
        select(m.User).where(m.User.email == "user1@example.com")
    ).one()
    assert existing_user.first_name != "John"
    assert existing_user.last_name != "Doe"
    new_user_data = {
        "id": existing_user.id,
        "first_name": "John",
        "last_name": "Doe",
        "email": "different@address.com",
    }
    response = client.put(f"/user/{existing_user.id}", json=new_user_data)
    assert response.status_code == 200
    session.refresh(existing_user)
    assert existing_user.first_name == "John"
    assert existing_user.last_name == "Doe"
    assert existing_user.email == "different@address.com"


def test_get_users(client, session):
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 3


def test_retrieve_token(client, session):
    data = {"username": "user1@example.com", "password": "DEBUG_PASSWORD"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )


def test_add_non_existing_initiative(client, session):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [42],
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "One or more instances of Initiative to link do not exist"
    )
    return response.json()


def test_add_existing_initiative(client, session):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1],
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    assert response.json()["initiatives"][0]["id"] == 1


def test_add_duplicate_initiatives(client, session):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1, 1],
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 404


def test_add_two_initiatives(client, session):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1, 2],
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    assert response.json()["initiatives"][0]["id"] in (1, 2)
    assert response.json()["initiatives"][1]["id"] in (1, 2)
    assert len(response.json()["initiatives"]) == 2
