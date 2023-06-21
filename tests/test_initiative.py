# from .fixtures import client, created_user
import pytest
from sqlmodel import select
from open_poen_api.schemas_and_models.models import entities as e


@pytest.mark.parametrize(
    "authorization_header_name, status_code, name_in_db",
    [
        ("admin_authorization_header", 200, True),
        ("financial_authorization_header", 403, False),
        ("user_authorization_header", 403, False),
        ("guest_authorization_header", 401, False),
    ],
)
def test_post_initiative(
    client,
    session_2,
    authorization_header_name,
    status_code,
    name_in_db,
    initiative_data,
    request,
):
    authorization_header, _ = request.getfixturevalue(authorization_header_name)
    response = client.post(
        "/initiative", json=initiative_data, headers=authorization_header
    )
    assert response.status_code == status_code
    name_exists = initiative_data["name"] in [
        initiative.name for initiative in session_2.exec(select(e.Initiative)).all()
    ]
    assert name_exists == name_in_db


def test_duplicate_name(client, session_2, admin_authorization_header, initiative_data):
    initiative_data["name"] = "Initiative 1"
    authorization_header, _ = admin_authorization_header
    response = client.post(
        "/initiative", json=initiative_data, headers=authorization_header
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Name already registered"


@pytest.mark.parametrize(
    "authorization_header_name, status_code",
    [
        ("admin_authorization_header", 200),
        ("financial_authorization_header", 403),
        ("user_authorization_header", 403),
        ("guest_authorization_header", 401),
    ],
)
def test_patch_initiative(
    client, session_2, authorization_header_name, status_code, request
):
    existing_initiative = session_2.exec(
        select(e.Initiative).where(e.Initiative.name == "Initiative 1")
    ).one()
    assert existing_initiative.name != "New Name"
    new_initiative_data = {
        "name": "New Name",
    }
    authorization_header, _ = request.getfixturevalue(authorization_header_name)
    response = client.patch(
        f"/initiative/{existing_initiative.id}",
        json=new_initiative_data,
        headers=authorization_header,
    )
    assert response.status_code == status_code
    if status_code not in (401, 403):
        session_2.refresh(existing_initiative)
        assert existing_initiative.name == "New Name"


@pytest.mark.parametrize(
    "authorization_header_name, should_see_owner_email",
    [
        ("admin_authorization_header", True),
        ("financial_authorization_header", False),
        ("user_authorization_header", False),
        ("guest_authorization_header", False),
    ],
)
def test_get_initiatives(
    client, session_2, authorization_header_name, should_see_owner_email, request
):
    authorization_header, _ = request.getfixturevalue(authorization_header_name)
    response = client.get(
        "/initiatives",
        headers=authorization_header,
    )
    assert response.status_code == 200
    response_json = response.json()
    assert "initiatives" in response_json
    initiatives = response_json["initiatives"]
    assert isinstance(initiatives, list)
    for initiative in initiatives:
        assert "name" in initiative
        if should_see_owner_email:
            assert "owner_email" in initiative
        else:
            assert "owner_email" not in initiative


def test_add_non_existing_initiative_owner(client, session_2, initiative_data):
    initiative_data = {
        **initiative_data,
        "initiative_owner_ids": [42],
    }

    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "One or more instances of User to link do not exist"
    )
