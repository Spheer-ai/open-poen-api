from open_poen_api.schemas_and_models.models import entities as e
from sqlmodel import select
import pytest


@pytest.mark.parametrize(
    "auth, status_code, email_in_db",
    [
        ("admin_auth_2", 200, True),
        ("financial_auth_2", 403, False),
        ("user_auth_2", 403, False),
        ("guest_auth_2", 401, False),
    ],
)
def test_post_user(client, session_2, auth, status_code, email_in_db, request):
    authorization_header, _, _, _ = request.getfixturevalue(auth)
    user_data = {
        "email": "janedoe@gmail.com",
        "role": "financial",
    }
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == status_code
    email_exists = "janedoe@gmail.com" in [
        i.email for i in session_2.exec(select(e.User)).all()
    ]
    assert email_exists == email_in_db


def test_duplicate_email(client, session_2, admin_auth_2):
    user_data = {
        "email": "user1@example.com",
    }
    authorization_header, _, _, _ = admin_auth_2
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email address already registered"


def test_update_email_to_none(client, session_2, admin_auth_2):
    new_user_data = {"email": None, "first_name": "mark"}
    header, _, _, _ = admin_auth_2
    response = client.patch(
        f"/user/1",
        json=new_user_data,
        headers=header,
    )
    assert response.status_code == 422


auth_data = {
    "admin_auth_2": {"user": 200, "admin": 200},
    "financial_auth_2": {"user": 403, "admin": 403},
    "user_auth_2": {"user": 403, "admin": 403},
    "user_owner_auth_2": {"user": 200, "admin": 403},
    "guest_auth_2": {"user": 401, "admin": 401},
}

user_data_set = [
    {
        "first_name": "New First Name",
        "last_name": "New Last Name",
        "email": "different@address.com",
    },
    {"hidden": True},
]


@pytest.mark.parametrize("auth", auth_data.keys())
@pytest.mark.parametrize("user_data", user_data_set)
def test_patch_user(client, session_2, auth, user_data, request):
    authorization_header, user_id, _, _ = request.getfixturevalue(auth)
    existing_user = session_2.get(e.User, user_id)

    # Validate initial state
    for field, new_value in user_data.items():
        assert getattr(existing_user, field) != new_value

    response = client.patch(
        f"/user/{existing_user.id}",
        json=user_data,
        headers=authorization_header,
    )

    status_code = (
        auth_data[auth].get("user")
        if "first_name" in user_data
        else auth_data[auth].get("admin")
    )
    assert response.status_code == status_code

    if status_code == 200:
        session_2.refresh(existing_user)
        for field, new_value in user_data.items():
            assert getattr(existing_user, field) == new_value


@pytest.mark.parametrize(
    "auth, status_code, should_see_email",
    [
        ("admin_auth_2", 200, True),
        ("financial_auth_2", 200, False),
        ("user_auth_2", 200, False),
        ("guest_auth_2", 401, False),
    ],
)
def test_get_users(client, session_2, auth, status_code, should_see_email, request):
    authorization_header, _, _, _ = request.getfixturevalue(auth)
    response = client.get(
        "/users",
        headers=authorization_header,
    )
    assert response.status_code == status_code
    if status_code == 200:
        response_json = response.json()
        assert "users" in response_json
        users = response_json["users"]
        assert isinstance(users, list)
        for user in users:
            if should_see_email:
                assert "email" in user
            else:
                assert "email" not in user


def test_retrieve_token(client, session_2):
    data = {"username": "user1@example.com", "password": "DEBUG_PASSWORD"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = client.post("/token", headers=headers, data=data)
    assert response.status_code == 200
    assert (
        "access_token" in response.json() and response.json()["token_type"] == "bearer"
    )


def test_add_non_existing_initiative(client, session_2, admin_auth_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [42],
    }
    authorization_header, _, _, _ = admin_auth_2
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "One or more instances of Initiative to link do not exist"
    )


def test_add_existing_initiative(client, session_2, admin_auth_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1],
    }
    authorization_header, _, _, _ = admin_auth_2
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == 200
    assert response.json()["initiatives"][0]["id"] == 1


def test_add_duplicate_initiatives(client, session_2, admin_auth_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1, 1],
    }
    authorization_header, _, _, _ = admin_auth_2
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == 404


def test_add_two_initiatives(client, session_2, admin_auth_2):
    user_data = {
        "email": "johndoe@gmail.com",
        "role": "admin",
        "initiative_ids": [1, 2],
    }
    authorization_header, _, _, _ = admin_auth_2
    response = client.post("/user", json=user_data, headers=authorization_header)
    assert response.status_code == 200
    assert response.json()["initiatives"][0]["id"] in (1, 2)
    assert response.json()["initiatives"][1]["id"] in (1, 2)
    assert len(response.json()["initiatives"]) == 2
