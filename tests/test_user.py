import open_poen_api.models as m
from sqlmodel import select
import pytest


@pytest.mark.parametrize(
    "authorization_header_name, status_code, email_in_db",
    [
        ("admin_authorization_header", 200, True),
        ("financial_authorization_header", 403, False),
        ("user_authorization_header", 403, False),
    ],
)
def test_create_user(
    client, session_2, authorization_header_name, status_code, email_in_db, request
):
    authorization_header = request.getfixturevalue(authorization_header_name)
    user_data = {
        "email": "janedoe@gmail.com",
        "role": "financial",
    }
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == status_code
    email_exists = "janedoe@gmail.com" in [
        i.email for i in session_2.exec(select(m.User)).all()
    ]
    assert email_exists == email_in_db


def test_duplicate_email(client, session_2):
    user_data = {
        "email": "user1@example.com",
    }

    response = client.post("/user", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email address already registered"


def test_delete_non_existing_user(client, session_2):
    response = client.delete("/user/42")
    assert response.status_code == 404
    assert session_2.get(m.User, 42) is None


def test_update_user(client, session_2):
    existing_user = session_2.exec(
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
    session_2.refresh(existing_user)
    assert existing_user.first_name == "John"
    assert existing_user.last_name == "Doe"
    assert existing_user.email == "different@address.com"


def test_get_users(client, session_2):
    response = client.get("/users")
    assert response.status_code == 200
    assert len(response.json()["users"]) == 3


def test_retrieve_token(client, session_2):
    data = {"username": "user1@example.com", "password": "DEBUG_PASSWORD"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )


def test_add_non_existing_initiative(client, session_2):
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


def test_add_existing_initiative(client, session_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1],
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 200
    assert response.json()["initiatives"][0]["id"] == 1


def test_add_duplicate_initiatives(client, session_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1, 1],
    }
    response = client.post("/user", json=user_data)
    assert response.status_code == 404


def test_add_two_initiatives(client, session_2):
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
