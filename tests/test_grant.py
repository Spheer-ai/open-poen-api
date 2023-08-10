import pytest
from tests.conftest import (
    superuser_info,
    user_info,
    admin_info,
    anon_info,
    grant_info,
)
from open_poen_api.models import Grant
from open_poen_api.managers import get_grant_manager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (admin_info, 200), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_create_grant(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    body = grant_info
    response = await async_client.post(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        db_grant = await dummy_session.get(Grant, response.json()["id"])
        assert db_grant is not None
        grant_data = response.json()
        assert grant_data["name"] == body["name"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 204), (user_info, 403), (admin_info, 204), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_delete_grant(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    response = await async_client.delete(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}"
    )
    assert response.status_code == status_code
    if status_code == 204:
        grant = await dummy_session.get(Grant, funder_id)
        assert grant is None


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", [1, None], ids=["Add", "Remove"])
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (admin_info, 200), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_add_overseer(async_client, dummy_session, status_code, user_id):
    funder_id, regulation_id, grant_id = 1, 1, 1
    body = {"user_id": user_id}
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/overseer",
        json=body,
    )
    assert response.status_code == status_code
    if status_code == 200:
        gm = await get_grant_manager(dummy_session).__anext__()
        db_grant = await gm.detail_load(grant_id)
        if user_id == 1:
            assert db_grant.overseer.email == "user1@example.com"
        else:
            assert db_grant.overseer is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"name": "Another Name"}, 200),
        (user_info, {"name": "Another Name"}, 403),
        (superuser_info, {"name": "Cultural Heritage Preservation Fund"}, 400),
    ],
    ids=["Superuser can", "User cannot", "Duplicate name fails"],
    indirect=["get_mock_user"],
)
async def test_patch_grant(async_client, dummy_session, body, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        grant = await dummy_session.get(Grant, grant_id)
        for key in body:
            assert getattr(grant, key) == body[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    ids=["Superuser sees everything", "Anon sees everything"],
    indirect=["get_mock_user"],
)
async def test_get_grants_list(async_client, dummy_session, status_code):
    funder_id, regulation_id = 1, 1
    response = await async_client.get(
        f"/funder/{funder_id}/regulation/{regulation_id}/grants"
    )
    assert response.status_code == status_code
    assert len(response.json()["grants"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    ids=["Superuser can", "Anon can"],
    indirect=["get_mock_user"],
)
async def test_get_linked_grant_detail(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    response = await async_client.get(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}"
    )
    assert response.status_code == status_code
