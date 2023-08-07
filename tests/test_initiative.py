import pytest
from tests.conftest import (
    superuser_info,
    userowner_info,
    user_info,
    anon_info,
    initiative_info,
)
from open_poen_api.models import Initiative
from open_poen_api.managers import get_initiative_manager


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_create_initiative(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    body = initiative_info
    response = await async_client.post(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/initiative",
        json=body,
    )
    assert response.status_code == status_code
    db_initiative = dummy_session.get(Initiative, response.json()["id"])
    assert db_initiative is not None
    initiative_data = response.json()
    assert initiative_data["name"] == body["name"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code", [(superuser_info, 204)], indirect=["get_mock_user"]
)
async def test_delete_initiative(async_client, as_2, status_code):
    initiative_id = 1
    response = await async_client.delete(f"/initiative/{initiative_id}")
    assert response.status_code == status_code
    if status_code == 204:
        initiative = await as_2.get(Initiative, initiative_id)
        assert initiative is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code", [(superuser_info, 200)], indirect=["get_mock_user"]
)
async def test_add_initiative_owner(async_client, as_2, status_code):
    initiative_id = 1
    body = {"user_ids": [1]}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/owners", json=body
    )
    assert response.status_code == status_code
    im = await get_initiative_manager(as_2).__anext__()
    db_initiative = await im.detail_load(initiative_id)
    assert len(db_initiative.initiative_owners) == 1
    assert db_initiative.initiative_owners[0].email == "existing@user.com"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code", [(superuser_info, 200)], indirect=["get_mock_user"]
)
async def test_add_debit_cards(async_client, as_2, status_code):
    initiative_id = 1
    body = {"card_numbers": [6731924123456789012]}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/debit-cards", json=body
    )
    assert response.status_code == status_code
    im = await get_initiative_manager(as_2).__anext__()
    db_initiative = await im.detail_load(initiative_id)
    assert len(db_initiative.debit_cards) == 1
    assert db_initiative.debit_cards[0].card_number == str(6731924123456789012)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser_info, {"location": "Groningen"}, 200),
        (userowner_info, {"location": "Groningen"}, 403),
        (superuser_info, {"hidden": True}, 200),
        (userowner_info, {"hidden": True}, 200),
        (user_info, {"location": "Groningen"}, 403),
        (superuser_info, {"name": "Piets Buurtbarbeque2"}, 400),
    ],
    indirect=["get_mock_user"],
)
async def test_patch_initiative(async_client, as_3, body, status_code):
    initiative_id = 1
    response = await async_client.patch(f"/initiative/{initiative_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        initiative = await as_3.get(Initiative, initiative_id)
        # Fix this. Apparently the session is not clean on every test invocation.
        await as_3.refresh(initiative)
        for key in body:
            assert getattr(initiative, key) == body[key]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    indirect=["get_mock_user"],
)
async def test_get_initiatives_list(async_client, as_3, status_code):
    response = await async_client.get("/initiatives")
    assert response.status_code == status_code
    assert len(response.json()["initiatives"]) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (anon_info, 200)],
    indirect=["get_mock_user"],
)
async def test_get_linked_initiative_detail(async_client, as_3, status_code):
    initiative_id = 1
    response = await async_client.get(f"/initiative/{initiative_id}")
    assert response.status_code == status_code


# # from .fixtures import client, created_user
# import pytest
# from sqlmodel import select
# from open_poen_api.schemas_and_models.models import entities as ent


# @pytest.mark.parametrize(
#     "auth, status_code, name_in_db",
#     [
#         ("admin_auth_2", 200, True),
#         ("financial_auth_2", 403, False),
#         ("user_auth_2", 403, False),
#         ("guest_auth_2", 401, False),
#     ],
# )
# def test_post_initiative(
#     client,
#     session_2,
#     auth,
#     status_code,
#     name_in_db,
#     initiative_data,
#     request,
# ):
#     authorization_header, _, _, _ = request.getfixturevalue(auth)
#     response = client.post(
#         "/initiative", json=initiative_data, headers=authorization_header
#     )
#     assert response.status_code == status_code
#     name_exists = initiative_data["name"] in [
#         initiative.name for initiative in session_2.exec(select(ent.Initiative)).all()
#     ]
#     assert name_exists == name_in_db


# def test_duplicate_name(client, session_2, user_admin_2, initiative_data):
#     initiative_data["name"] = "Initiative 1"
#     authorization_header, _, _, _ = user_admin_2
#     response = client.post(
#         "/initiative", json=initiative_data, headers=authorization_header
#     )
#     assert response.status_code == 400
#     assert response.json()["detail"] == "Name already registered"


# @pytest.mark.parametrize(
#     "auth, status_code",
#     [
#         ("admin_auth_2", 200),
#         ("financial_auth_2", 200),
#         ("initiative_owner_auth_2", 200),
#         ("guest_auth_2", 401),
#     ],
# )
# def test_patch_initiative(client, session_2, auth, status_code, request):
#     authorization_header, user_id, initiative_id, _ = request.getfixturevalue(auth)
#     existing_initiative = session_2.get(ent.Initiative, initiative_id)
#     assert existing_initiative.name != "New Name"
#     new_initiative_data = {
#         "name": "New Name",
#     }
#     response = client.patch(
#         f"/initiative/{existing_initiative.id}",
#         json=new_initiative_data,
#         headers=authorization_header,
#     )
#     assert response.status_code == status_code
#     if status_code not in (401, 403):
#         session_2.refresh(existing_initiative)
#         assert existing_initiative.name == "New Name"


# @pytest.mark.parametrize(
#     "auth, should_see_owner_email",
#     [
#         ("admin_auth_2", True),
#         ("financial_auth_2", False),
#         ("user_auth_2", False),
#         ("guest_auth_2", False),
#     ],
# )
# def test_get_initiatives(client, session_2, auth, should_see_owner_email, request):
#     authorization_header, _, _, _ = request.getfixturevalue(auth)
#     response = client.get(
#         "/initiatives",
#         headers=authorization_header,
#     )
#     assert response.status_code == 200
#     response_json = response.json()
#     assert "initiatives" in response_json
#     initiatives = response_json["initiatives"]
#     assert isinstance(initiatives, list)
#     for initiative in initiatives:
#         assert "name" in initiative
#         if should_see_owner_email:
#             assert "owner_email" in initiative
#         else:
#             assert "owner_email" not in initiative


# def test_add_non_existing_initiative_owner(
#     client, session_2, user_admin_2, initiative_data
# ):
#     authorization_header, _, _, _ = user_admin_2
#     initiative_data = {
#         **initiative_data,
#         "initiative_owner_ids": [42],
#     }

#     response = client.post(
#         "/initiative", json=initiative_data, headers=authorization_header
#     )
#     assert response.status_code == 404
#     assert (
#         response.json()["detail"]
#         == "One or more instances of User to link do not exist"
#     )
