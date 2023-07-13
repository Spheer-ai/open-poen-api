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
