from .fixtures import client, created_user


def test_create_initiative(client, created_user):
    initiative_data = {
        "name": "Piets Buurtbarbeque",
        "description": "Piet wordt vijftig.",
        "purpose": "Saamhorigheid in de buurt bevorderen.",
        "target_audience": "Mensen uit buurt De Florijn.",
        "owner": "Mark de Wijk",
        "owner_email": "markdewijk@spheer.ai",
        "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
        "kvk_registration": "12345678",
        "location": "Amsterdam",
        "initiative_owner_ids": [created_user["id"]],
    }
    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 200

    created_user.pop("initiatives")
    assert response.json()["initiative_owners"][0] == created_user
    assert response.json()["name"] == "Piets Buurtbarbeque"


def test_update_initiative(client, created_user):
    initiative_data = {
        "name": "Piets Buurtbarbeque",
        "description": "Piet wordt vijftig.",
        "purpose": "Saamhorigheid in de buurt bevorderen.",
        "target_audience": "Mensen uit buurt De Florijn.",
        "owner": "Mark de Wijk",
        "owner_email": "markdewijk@spheer.ai",
        "address_applicant": "Het stoepje 42, Assen, 9408DT, Nederland",
        "kvk_registration": "12345678",
        "location": "Amsterdam",
        "initiative_owner_ids": [created_user["id"]],
    }
    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 200

    initiative_data["name"] = "Andere naam"
    response = client.put("/initiative/1", json=initiative_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Andere naam"
