# from .fixtures import client, created_user
import pytest
from sqlmodel import select
import open_poen_api.models as m


@pytest.fixture
def initiative_data():
    return {
        "name": "Piets Buurtbarbeque",
        "description": "Piet wordt vijftig.",
        "purpose": "Saamhorigheid in de buurt bevorderen.",
        "target_audience": "Mensen uit buurt De Florijn.",
        "owner": "Mark de Wijk",
        "owner_email": "markdewijk@spheer.ai",
        "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
        "kvk_registration": "12345678",
        "location": "Amsterdam",
    }


def test_create_initiative(client, session_2, initiative_data):
    initiative_data = {
        **initiative_data,
        "initiative_owner_ids": [1, 2, 3],
    }
    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 200
    initiative = session_2.get(m.Initiative, response.json()["id"])
    assert len(initiative.initiative_owners) == 3


def test_duplicate_name(client, session_2, initiative_data):
    initiative_data["name"] = "Initiative 1"
    initiative_data["initiative_owner_ids"] = []

    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Name already registered"


def test_delete_non_existing_initiative(client, session_2):
    response = client.delete("/initiative/42")
    assert response.status_code == 404
    assert session_2.get(m.Initiative, 42) is None


def test_update_initiative(client, session_2):
    existing_initiative = session_2.exec(
        select(m.Initiative).where(m.Initiative.name == "Initiative 1")
    ).one()
    assert existing_initiative.description != "New Description"
    assert existing_initiative.purpose != "New Purpose"

    new_initiative_data = {
        "id": existing_initiative.id,
        "name": "Initiative 1",
        "description": "New Description",
        "purpose": "New Purpose",
        "target_audience": "Target Audience 1",
        "owner": "Owner 1",
        "owner_email": "email1@example.com",
        "address_applicant": "Address 1",
        "kvk_registration": "Registration 1",
        "location": "Location 1",
        "hidden": True,
        "initiative_owner_ids": [1, 2],
    }

    response = client.put(
        f"/initiative/{existing_initiative.id}", json=new_initiative_data
    )
    assert response.status_code == 200

    session_2.refresh(existing_initiative)
    assert existing_initiative.description == "New Description"
    assert existing_initiative.purpose == "New Purpose"


def test_get_initiatives(client, session_2):
    response = client.get("/initiatives")
    assert response.status_code == 200
    assert len(response.json()["initiatives"]) == 2


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
