import pytest
from sqlmodel import select, and_
import open_poen_api.models as m


@pytest.fixture
def activity_data():
    return {
        "name": "Vlees- en Drinkwaren",
        "description": "Eten voor de barbeque",
        "purpose": "Ervoor zorgen dat er voldoende te eten en te drinken is",
        "target_audience": "Alle bezoekers",
        "activity_owner_ids": [1],
    }


def test_create_activity(client, session_3, activity_data):
    response = client.post("/initiative/1/activity", json=activity_data)
    assert response.status_code == 200
    activity = session_3.get(m.Activity, response.json()["id"])
    assert len(activity.activity_owners) == 1


def test_create_activity_for_non_existing_initiative(client, session_3, activity_data):
    response = client.post("/initiative/42/activity", json=activity_data)
    assert response.status_code == 404


def test_duplicate_name(client, session_3, activity_data):
    activity_data["name"] = "Activity 1"
    response = client.post("/initiative/1/activity", json=activity_data)
    assert response.status_code == 400
    assert (
        response.json()["detail"] == "Initiative already has an activity with this name"
    )


def test_delete_non_existing_activity(client, session_3):
    response = client.delete("/initiative/1/activity/42")
    assert response.status_code == 404
    assert session_3.get(m.Activity, 42) is None


def test_update_activity(client, session_3):
    existing_activity = session_3.exec(
        select(m.Activity).where(
            and_(m.Activity.name == "Activity 1"), m.Initiative.id == 1
        )
    ).one()
    assert existing_activity.description != "New Description"
    assert existing_activity.purpose != "New Purpose"

    new_initiative_data = {
        "id": existing_activity.id,
        "name": "Activity 1",
        "description": "New Description",
        "purpose": "New Purpose",
        "target_audience": "Target Audience 1",
    }
    url = (
        f"/initiative/{existing_activity.initiative_id}"
        "/activity"
        f"/{existing_activity.id}"
    )
    response = client.put(url, json=new_initiative_data)
    assert response.status_code == 200

    session_3.refresh(existing_activity)
    assert existing_activity.description == "New Description"
    assert existing_activity.purpose == "New Purpose"


def test_get_activities(client, session_3):
    response = client.get("/initiative/1/activities")
    assert response.status_code == 200
    assert len(response.json()["activities"]) == 2


def test_add_non_existing_activity_owner(client, session_3, activity_data):
    activity_data["activity_owner_ids"] = [42]
    response = client.post("/initiative/1/activity/", json=activity_data)
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "One or more instances of User to link do not exist"
    )
