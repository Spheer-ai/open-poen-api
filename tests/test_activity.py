import pytest
from tests.conftest import (
    superuser,
    admin,
    grant_officer,
    initiative_owner,
    activity_owner,
    user,
    anon,
    activity_info,
)
from open_poen_api.models import Activity, Initiative
from open_poen_api.managers.activity_manager import ActivityManager


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
        (admin, 200),
        (grant_officer, 200),
        (initiative_owner, 200),
        (user, 403),
        (anon, 403),
    ],
    ids=[
        "Superuser can",
        "Administrator can",
        "Policy officer can",
        "Initiative owner can",
        "User cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_create_activity(async_client, dummy_session, status_code):
    body = activity_info
    initiative_id = 1
    response = await async_client.post(
        f"/initiative/{initiative_id}/activity", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        db_activity = dummy_session.get(Activity, response.json()["id"])
        assert db_activity is not None
        activity_data = response.json()
        assert activity_data["name"] == body["name"]


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 204),
        (admin, 204),
        (grant_officer, 204),
        (initiative_owner, 204),
        (activity_owner, 403),
        (user, 403),
        (anon, 403),
    ],
    ids=[
        "Superuser can",
        "Administrator can",
        "Policy officer can",
        "Initiative owner can",
        "Activity owner cannot",
        "User cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_delete_activity(async_client, dummy_session, status_code):
    initiative_id, activity_id = 1, 1
    response = await async_client.delete(
        f"/initiative/{initiative_id}/activity/{activity_id}"
    )
    assert response.status_code == status_code
    if status_code == 204:
        activity = await dummy_session.get(Activity, activity_id)
        assert activity is None
        initiative = await dummy_session.get(Initiative, initiative_id)
        assert initiative is not None


@pytest.mark.parametrize(
    "get_mock_user, ids, status_code",
    [
        (superuser, [2], 200),
        (superuser, [], 200),
        (superuser, [2, 999], 404),
        (superuser, [2, 3, 4], 200),
        (user, [2], 403),
        (admin, [2], 200),
        (grant_officer, [2], 200),
        (initiative_owner, [2], 200),
        (activity_owner, [2], 403),
        (anon, [2], 403),
    ],
    ids=[
        "Superuser can",
        "Remove all",
        "Unknown returns 404",
        "Assign multiple",
        "User cannot",
        "Admin can",
        "Policy officer can",
        "Initiative owner can",
        "Activity owner cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_add_activity_owner(async_client, dummy_session, ids, status_code):
    initiative_id, activity_id = 1, 1
    body = {"user_ids": ids}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/activity/{activity_id}/owners", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        am = ActivityManager(dummy_session, None)
        db_activity = await am.detail_load(activity_id)
        assert set([i.id for i in db_activity.activity_owners]) == set(ids)


@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser, {"hidden": True}, 200),
        (admin, {"hidden": True}, 200),
        (grant_officer, {"hidden": True}, 200),
        (initiative_owner, {"hidden": True}, 200),
        (activity_owner, {"hidden": True}, 403),
        (activity_owner, {"description": "New description."}, 200),
        (user, {"description": "New description."}, 403),
        (anon, {"description": "New description."}, 403),
        (superuser, {"name": "Community Cleanup Day"}, 400),
    ],
    ids=[
        "Superuser can hide",
        "Administrator can hide",
        "Policy officer can hide",
        "Initiative owner can hide",
        "Activity owner cannot hide",
        "Activity owner can edit description",
        "User cannot edit description",
        "Anon cannot edit description",
        "Duplicate name fails",
    ],
    indirect=["get_mock_user"],
)
async def test_patch_activity(async_client, dummy_session, body, status_code):
    initiative_id, activity_id = 1, 1
    response = await async_client.patch(
        f"/initiative/{initiative_id}/activity/{activity_id}", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        activity = await dummy_session.get(Activity, activity_id)
        # Fix this. Apparently the session is not clean on every test invocation.
        await dummy_session.refresh(activity)
        for key in body:
            assert getattr(activity, key) == body[key]


@pytest.mark.parametrize(
    "get_mock_user, field, present, status_code",
    [
        (superuser, "budget", True, 200),
        (anon, "budget", True, 200),
        (activity_owner, "hidden", True, 200),
        (initiative_owner, "hidden", True, 200),
        (grant_officer, "hidden", True, 200),
        (admin, "hidden", True, 200),
        (superuser, "hidden", True, 200),
        (user, "hidden", False, 200),
        (anon, "hidden", False, 200),
    ],
    ids=[
        "Superuser can see budget",
        "Anon can see budget",
        "Activity owner can see hidden",
        "Initiative owner can see hidden",
        "Policy officer can see hidden",
        "Admin can see hidden",
        "Superuser can see hidden",
        "User cannot see hidden",
        "Anon cannot see hidden",
    ],
    indirect=["get_mock_user"],
)
async def test_get_linked_activity_detail(
    async_client, dummy_session, field, present, status_code
):
    initiative_id, activity_id = 1, 1
    response = await async_client.get(
        f"/initiative/{initiative_id}/activity/{activity_id}"
    )
    assert response.status_code == status_code
    assert (field in response.json().keys()) == present
