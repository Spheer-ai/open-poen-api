import pytest
from tests.conftest import (
    superuser,
    initiative_owner,
    activity_owner,
    user,
    admin,
    anon,
    initiative_info,
    grant_officer,
    hide_instance,
)
from open_poen_api.models import Initiative
from open_poen_api.managers import InitiativeManager


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
        (user, 403),
        (admin, 200),
        (anon, 403),
        (grant_officer, 200),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Anon cannot",
        "Policy officer can",
    ],
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
    if status_code == 200:
        db_initiative = dummy_session.get(Initiative, response.json()["id"])
        assert db_initiative is not None
        initiative_data = response.json()
        assert initiative_data["name"] == body["name"]


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 204),
        (user, 403),
        (admin, 204),
        (anon, 403),
        (grant_officer, 204),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Anon cannot",
        "Policy officer can",
    ],
    indirect=["get_mock_user"],
)
async def test_delete_initiative(async_client, dummy_session, status_code):
    initiative_id = 1
    response = await async_client.delete(f"/initiative/{initiative_id}")
    assert response.status_code == status_code
    if status_code == 204:
        initiative = await dummy_session.get(Initiative, initiative_id)
        assert initiative is None


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
        (user, 403),
        (admin, 200),
        (anon, 403),
        (grant_officer, 200),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Anon cannot",
        "Policy officer can",
    ],
    indirect=["get_mock_user"],
)
async def test_add_initiative_owner(async_client, dummy_session, status_code):
    initiative_id = 1
    body = {"user_ids": [1]}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/owners", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        im = InitiativeManager(dummy_session, None)
        db_initiative = await im.detail_load(initiative_id)
        assert len(db_initiative.initiative_owners) == 1
        assert db_initiative.initiative_owners[0].email == "user1@example.com"


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
        (user, 403),
        (admin, 200),
        (anon, 403),
        (grant_officer, 403),
    ],
    ids=[
        "Superuser can",
        "User cannot",
        "Administrator can",
        "Anon cannot",
        "Policy officer cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_add_debit_cards(async_client, dummy_session, status_code):
    initiative_id = 1
    body = {"card_numbers": [6731924123456789012]}
    response = await async_client.patch(
        f"/initiative/{initiative_id}/debit-cards", json=body
    )
    assert response.status_code == status_code
    if status_code == 200:
        im = InitiativeManager(dummy_session, None)
        db_initiative = await im.detail_load(initiative_id)
        assert len(db_initiative.debit_cards) == 1
        assert db_initiative.debit_cards[0].card_number == str(6731924123456789012)


@pytest.mark.parametrize(
    "get_mock_user, body, status_code",
    [
        (superuser, {"location": "Groningen"}, 200),
        (grant_officer, {"location": "Groningen"}, 200),
        (initiative_owner, {"location": "Groningen"}, 403),
        (user, {"location": "Groningen"}, 403),
        (superuser, {"hidden": True}, 200),
        (grant_officer, {"hidden": True}, 200),
        (initiative_owner, {"hidden": True}, 403),
        (user, {"hidden": True}, 403),
        (superuser, {"name": "Community Health Initiative"}, 400),
    ],
    ids=[
        "Superuser edits loc",
        "Policy officer edits loc",
        "Initiative owner cannot edit loc",
        "User cannot edit loc",
        "Superuser can hide",
        "Policy officer can hide",
        "Initiative owner cannot hide",
        "User cannot hide",
        "Duplicate name fails",
    ],
    indirect=["get_mock_user"],
)
async def test_patch_initiative(async_client, dummy_session, body, status_code):
    initiative_id = 1
    response = await async_client.patch(f"/initiative/{initiative_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        initiative = await dummy_session.get(Initiative, initiative_id)
        for key in body:
            assert getattr(initiative, key) == body[key]


@pytest.mark.parametrize(
    "get_mock_user, result_length, status_code",
    [
        (superuser, 24, 200),
        (admin, 24, 200),
        (grant_officer, 23, 200),
        (initiative_owner, 22, 200),
        (activity_owner, 22, 200),
        (user, 21, 200),
        (anon, 21, 200),
    ],
    ids=[
        "Superuser sees everything",
        "Administrator sees everything",
        "Policy officer sees own hidden initiatives",
        "initiative_owner sees own hidden initiative",
        "activity_owner sees own hidden initiative",
        "User sees non hidden",
        "Anon sees non hidden",
    ],
    indirect=["get_mock_user"],
)
async def test_get_initiatives_list(
    async_client, dummy_session, status_code, result_length
):
    await hide_instance(dummy_session, Initiative, 1)
    response = await async_client.get("/initiatives")
    assert response.status_code == status_code
    assert len(response.json()["initiatives"]) == result_length


@pytest.mark.parametrize(
    "get_mock_user, field, present, status_code",
    [
        (superuser, "address_applicant", True, 200),
        (grant_officer, "address_applicant", True, 200),
        (initiative_owner, "address_applicant", True, 200),
        (user, "address_applicant", False, 200),
        (anon, "address_applicant", False, 200),
    ],
    ids=[
        "Superuser can see address",
        "Policy officer can see address",
        "Initiative owner can see address",
        "User cannot see address",
        "Anon cannot see address",
    ],
    indirect=["get_mock_user"],
)
async def test_get_linked_initiative_detail(
    async_client, dummy_session, field, present, status_code
):
    initiative_id = 1
    response = await async_client.get(f"/initiative/{initiative_id}")
    assert response.status_code == status_code
    assert (field in response.json().keys()) == present
