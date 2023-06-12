from .fixtures import client, created_user


def test_create_initiative(client, created_user):
    initiative_data = {
        "name": "New Initiative",
        "initiative_owners": ["johndoe@gmail.com"],
    }
    response = client.post("/initiative", json=initiative_data)
    assert response.status_code == 200
    initiative = response.json()
    assert "id" in initiative
    assert initiative["name"] == "New Initiative"
