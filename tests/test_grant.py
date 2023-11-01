import pytest
from tests.conftest import (
    superuser,
    user,
    admin,
    anon,
    grant_info,
    grant_officer,
)
from open_poen_api.models import Grant
from open_poen_api.managers import GrantManager


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
        (user, 403),
        (admin, 200),
        (grant_officer, 200),
        (anon, 403),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Grant officer can",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_create_grant(async_client, dummy_session, status_code):
    funder_id, regulation_id = 2, 6
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


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 204),
        (user, 403),
        (admin, 204),
        (grant_officer, 204),
        (anon, 403),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Policy officer can",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_delete_grant(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 2, 6, 1
    response = await async_client.delete(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}"
    )
    assert response.status_code == status_code
    if status_code == 204:
        grant = await dummy_session.get(Grant, grant_id)
        assert grant is None


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (user, 403), (admin, 200), (anon, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_add_overseers(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    body = {"user_ids": [1]}
    response = await async_client.patch(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/overseers",
        json=body,
    )
    assert response.status_code == status_code
    if status_code == 200:
        gm = GrantManager(dummy_session, None)
        db_grant = await gm.detail_load(grant_id)
        assert db_grant.overseers[0].email == "user1@example.com"


@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser, {"name": "Another Name"}, 200),
        (admin, {"name": "Another Name"}, 200),
        (user, {"name": "Another Name"}, 403),
        (grant_officer, {"name": "Another name"}, 200),
        (superuser, {"name": "Cultural Heritage Preservation Fund"}, 400),
    ],
    ids=[
        "Superuser can",
        "Admin can",
        "User cannot",
        "Policy officer can",
        "Duplicate name fails",
    ],
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


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (anon, 200)],
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


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (anon, 200)],
    ids=["Superuser can", "Anon can"],
    indirect=["get_mock_user"],
)
async def test_get_linked_grant_detail(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    response = await async_client.get(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}"
    )
    assert response.status_code == status_code
