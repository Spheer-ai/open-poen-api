import pytest
from tests.conftest import superuser, user, admin, anon, regulation_info, grant_officer
from open_poen_api.models import Regulation
from open_poen_api.managers import RegulationManager


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (user, 403), (admin, 200), (grant_officer, 403), (anon, 403)],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Policy officer cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_create_regulation(async_client, dummy_session, status_code):
    funder_id = 1
    body = regulation_info
    response = await async_client.post(f"/funder/{funder_id}/regulation", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        db_regulation = await dummy_session.get(Regulation, response.json()["id"])
        assert db_regulation is not None
        regulation_data = response.json()
        assert regulation_data["name"] == body["name"]


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 204), (user, 403), (admin, 204), (grant_officer, 403), (anon, 403)],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Policy officer cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_delete_regulation(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    response = await async_client.delete(
        f"/funder/{funder_id}/regulation/{regulation_id}"
    )
    assert response.status_code == status_code
    if status_code == 204:
        regulation = await dummy_session.get(Regulation, funder_id)
        assert regulation is None


@pytest.mark.parametrize("role", ["grant officer", "policy officer"])
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (user, 403), (admin, 200), (grant_officer, 403), (anon, 403)],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Policy officer cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_add_officer(async_client, dummy_session, status_code, role):
    funder_id, regulation_id = 1, 1
    body = {"user_ids": [1], "role": role}
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}/officers", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        rm = RegulationManager(dummy_session, None)
        db_regulation = await rm.detail_load(regulation_id)
        officers = (
            db_regulation.grant_officers
            if role == "grant officer"
            else db_regulation.policy_officers
        )
        assert len(officers) == 1
        assert officers[0].email == "user1@example.com"


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200)],
    ids=[
        "Single user can be both officers",
    ],
    indirect=["get_mock_user"],
)
async def test_officer_can_have_double_role(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    body1 = {"user_ids": [1], "role": "policy officer"}
    body2 = {"user_ids": [1], "role": "grant officer"}
    for body in (body1, body2):
        response = await async_client.patch(
            f"/funder/{funder_id}/regulation/{regulation_id}/officers", json=body
        )
        assert response.status_code == status_code
    rm = RegulationManager(dummy_session, None)
    db_regulation = await rm.detail_load(regulation_id)
    assert len(db_regulation.grant_officers) == len(db_regulation.policy_officers) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser, {"name": "Another Name"}, 200),
        (user, {"name": "Another Name"}, 403),
        (grant_officer, {"name": "Another name"}, 403),
        (superuser, {"name": "Consumer Safety Guidelines"}, 409),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Policy officer cannot",
        "Duplicate name fails",
    ],
    indirect=["get_mock_user"],
)
async def test_patch_regulation(async_client, dummy_session, body, status_code):
    funder_id, regulation_id = 1, 1
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        regulation = await dummy_session.get(Regulation, funder_id)
        for key in body:
            assert getattr(regulation, key) == body[key]


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (grant_officer, 200), (anon, 200)],
    ids=[
        "Superuser sees everything",
        "Policy officer sees everything",
        "Anon sees everything",
    ],
    indirect=["get_mock_user"],
)
async def test_get_regulations_list(async_client, dummy_session, status_code):
    funder_id = 1
    response = await async_client.get(f"/funder/{funder_id}/regulations")
    assert response.status_code == status_code
    assert len(response.json()["regulations"]) == 5


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (anon, 200)],
    ids=["Superuser can", "Anon can"],
    indirect=["get_mock_user"],
)
async def test_get_linked_regulation_detail(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    response = await async_client.get(f"/funder/{funder_id}/regulation/{regulation_id}")
    assert response.status_code == status_code
