import pytest
from fastapi.testclient import TestClient
from open_poen_api.app import app


client = TestClient(app)


@pytest.fixture
def initiative_id():
    return 123


def test_create_activity(initiative_id):
    activity_data = {
        "name": "Sample Activity",
        "date_of_creation": "2023-06-07T12:00:00",
    }

    response = client.post(f"/initiative/{initiative_id}/activity", json=activity_data)

    assert response.status_code == 200
    activity = response.json()
    assert activity == activity_data
