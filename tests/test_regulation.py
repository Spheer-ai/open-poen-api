import pytest
from tests.conftest import (
    superuser_info,
    user_info,
    admin_info,
    anon_info,
    regulation_info,
)
from open_poen_api.models import Regulation
from open_poen_api.managers import get_regulation_manager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (admin_info, 200), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_create_regulation(async_client, dummy_session, status_code):
    funder_id = 1
    body = regulation_info
    response = await async_client.post(f"/funder/{funder_id}/regulation", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        db_regulation = dummy_session.get(Regulation, response.json()["id"])
        assert db_regulation is not None
        regulation_data = response.json()
        assert regulation_data["name"] == body["name"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 204), (user_info, 403), (admin_info, 204), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (admin_info, 200), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_add_grant_officer(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    body = {"user_ids": [1], "permission": "grant officer"}
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}/officers", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        rm = await get_regulation_manager(dummy_session).__anext__()
        db_regulation = await rm.detail_load(regulation_id)
        assert len(db_regulation.grant_officers) == 1
        assert db_regulation.grant_officers[0].email == "user1@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"name": "Another Name"}, 200),
        (user_info, {"name": "Another Name"}, 403),
        (superuser_info, {"name": "Healthcare Quality Assurance"}, 400),
    ],
    ids=["Superuser can", "User cannot", "Duplicate name fails"],
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    ids=["Superuser sees everything", "Anon sees everything"],
    indirect=["get_mock_user"],
)
async def test_get_regulations_list(async_client, dummy_session, status_code):
    funder_id = 1
    response = await async_client.get(f"/funder/{funder_id}/regulations")
    assert response.status_code == status_code
    assert len(response.json()["regulations"]) == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    ids=["Superuser can", "Anon can"],
    indirect=["get_mock_user"],
)
async def test_get_linked_regulation_detail(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    response = await async_client.get(f"/funder/{funder_id}/regulation/{regulation_id}")
    assert response.status_code == status_code
