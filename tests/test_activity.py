import pytest
from tests.conftest import (
    superuser_info,
    userowner_info,
    user_info,
    anon_info,
    activity_info,
)
from open_poen_api.models import Activity, Initiative
from open_poen_api.managers.activity_manager import get_activity_manager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser_info, 200),
        (userowner_info, 200),
        (user_info, 403),
        (anon_info, 403),
    ],
    indirect=["get_mock_user"],
)
async def test_create_activity(async_client, as_3, status_code):
    body = activity_info
    initiative_id = 1
    response = await async_client.post(
        f"/initiative/{initiative_id}/activity", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        db_activity = as_3.get(Activity, response.json()["id"])
        assert db_activity is not None
        activity_data = response.json()
        assert activity_data["name"] == body["name"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code", [(superuser_info, 204)], indirect=["get_mock_user"]
)
async def test_delete_activity(async_client, as_4, status_code):
    initiative_id, activity_id = 1, 1
    response = await async_client.delete(
        f"/initiative/{initiative_id}/activity/{activity_id}"
    )
    assert response.status_code == status_code
    if status_code == 204:
        activity = await as_4.get(Activity, activity_id)
        assert activity is None
        initiative = await as_4.get(Initiative, initiative_id)
        assert initiative is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, ids, status_code",
    [
        (superuser_info, [2], 200),
        (superuser_info, [], 200),
        (superuser_info, [2, 999], 404),
        (superuser_info, [2, 3, 4], 200),
    ],
    indirect=["get_mock_user"],
)
async def test_add_activity_owner(async_client, as_5, ids, status_code):
    initiative_id, activity_id = 1, 1
    body = {"user_ids": ids}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/activity/{activity_id}/owners", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        am = await get_activity_manager(as_5).__anext__()
        db_activity = await am.detail_load(initiative_id, activity_id)
        assert set([i.id for i in db_activity.activity_owners]) == set(ids)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"hidden": True}, 200),
    ],
    indirect=["get_mock_user"],
)
async def test_patch_activity(async_client, as_4, body, status_code):
    initiative_id, activity_id = 1, 1
    response = await async_client.patch(
        f"/initiative/{initiative_id}/activity/{activity_id}", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        activity = await as_4.get(Activity, activity_id)
        # Fix this. Apparently the session is not clean on every test invocation.
        await as_4.refresh(activity)
        for key in body:
            assert getattr(activity, key) == body[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    indirect=["get_mock_user"],
)
async def test_get_activity_detail(async_client, as_4, status_code):
    initiative_id, activity_id = 1, 1
    response = await async_client.get(
        f"/initiative/{initiative_id}/activity/{activity_id}"
    )
    assert response.status_code == status_code


# import pytest
# from sqlmodel import select, and_
# from open_poen_api.schemas_and_models.models import entities as ent


# @pytest.mark.parametrize(
#     "authorization_header_name, status_code, name_in_db",
#     [
#         ("admin_authorization_header", 200, True),
#         ("financial_authorization_header", 403, False),
#         ("user_authorization_header", 403, False),
#         ("guest_authorization_header", 401, False),
#     ],
# )
# def test_post_activity(
#     client,
#     session_3,
#     authorization_header_name,
#     status_code,
#     name_in_db,
#     activity_data,
#     request,
# ):
#     authorization_header, _ = request.getfixturevalue(authorization_header_name)
#     initiative_id = 1  # choose an appropriate initiative_id for your test scenario
#     response = client.post(
#         f"/initiative/{initiative_id}/activity",
#         json=activity_data,
#         headers=authorization_header,
#     )
#     assert response.status_code == status_code
#     name_exists = activity_data["name"] in [
#         activity.name for activity in session_3.exec(select(ent.Activity)).all()
#     ]
#     assert name_exists == name_in_db


# def test_duplicate_name(client, session_3, user_admin_2, activity_data):
#     activity_data["name"] = "Activity 1"
#     authorization_header, _ = user_admin_2
#     response = client.post(
#         "/initiative/1/activity", json=activity_data, headers=authorization_header
#     )
#     assert response.status_code == 400
#     assert (
#         response.json()["detail"] == "Initiative already has an activity with this name"
#     )


# @pytest.mark.parametrize(
#     "authorization_header_name, status_code",
#     [
#         ("admin_authorization_header", 200),
#         ("financial_authorization_header", 403),
#         ("user_authorization_header", 403),
#         ("guest_authorization_header", 401),
#     ],
# )
# def test_patch_activity(
#     client, session_3, authorization_header_name, status_code, request
# ):
#     existing_activity = session_3.exec(
#         select(ent.Activity).where(ent.Activity.name == "Activity 1")
#     ).one()
#     assert existing_activity.description != "Updated description"
#     assert existing_activity.purpose != "Updated purpose"
#     new_activity_data = {
#         "description": "Updated description",
#         "purpose": "Updated purpose",
#     }
#     authorization_header, _ = request.getfixturevalue(authorization_header_name)
#     response = client.patch(
#         f"/initiative/{existing_activity.initiative_id}/activity/{existing_activity.id}",
#         json=new_activity_data,
#         headers=authorization_header,
#     )
#     assert response.status_code == status_code
#     if status_code not in (401, 403):
#         session_3.refresh(existing_activity)
#         assert existing_activity.description == "Updated description"
#         assert existing_activity.purpose == "Updated purpose"


# @pytest.mark.parametrize(
#     "authorization_header_name, status_code, should_see_hidden",
#     [
#         ("admin_authorization_header", 200, True),
#         ("financial_authorization_header", 200, False),
#         ("user_authorization_header", 200, False),
#         ("guest_authorization_header", 200, False),
#     ],
# )
# def test_get_activities(
#     client,
#     session_2,
#     authorization_header_name,
#     status_code,
#     should_see_hidden,
#     request,
# ):
#     initiative_id = 1
#     authorization_header, _ = request.getfixturevalue(authorization_header_name)
#     response = client.get(
#         f"/initiative/{initiative_id}/activities",
#         headers=authorization_header,
#     )
#     assert response.status_code == status_code
#     response_json = response.json()
#     assert "activities" in response_json
#     activities = response_json["activities"]
#     assert isinstance(activities, list)
#     for activity in activities:
#         if should_see_hidden:
#             assert "hidden" in activity
#         else:
#             assert "hidden" not in activity
