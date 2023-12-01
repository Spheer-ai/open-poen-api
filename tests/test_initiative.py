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
        "Grant officer can",
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
        (superuser, 409),
    ],
    ids=[
        "Duplicate name fails with 400",
    ],
    indirect=["get_mock_user"],
)
async def test_duplicate_name(async_client, dummy_session, status_code):
    funder_id, regulation_id, grant_id = 1, 1, 1
    body = initiative_info
    body.update({"name": "Clean Energy Research Initiative"})
    response = await async_client.post(
        f"/funder/{funder_id}/regulation/{regulation_id}/grant/{grant_id}/initiative",
        json=body,
    )
    assert response.status_code == status_code
    assert (
        response.json()
        == "The following unique constraint was violated: 'unique initiative name'."
    )


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
        "Grant officer can",
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
        "Grant officer can",
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
        (superuser, {"name": "Community Health Initiative"}, 409),
    ],
    ids=[
        "Superuser edits loc",
        "Grant officer edits loc",
        "Initiative owner cannot edit loc",
        "User cannot edit loc",
        "Superuser can hide",
        "Grant officer can hide",
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
        (grant_officer, 24, 200),
        (initiative_owner, 22, 200),
        (activity_owner, 22, 200),
        (user, 21, 200),
        (anon, 21, 200),
    ],
    ids=[
        "Superuser sees everything",
        "Administrator sees everything",
        "Grant officer sees everything",
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
    response = await async_client.get("/initiatives?limit=100")
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
        "Grant officer can see address",
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


@pytest.mark.parametrize(
    "get_mock_user, length",
    [(superuser, 11), (initiative_owner, 11), (activity_owner, 10), (user, 9)],
    ids=[
        "Super user sees also hidden payments",
        "Initiative owner sees also hidden payment",
        "Activity owner sees own hidden payment in activity",
        "User cannot see any hidden payments",
    ],
    indirect=["get_mock_user"],
)
async def test_get_initiative_payments(async_client, dummy_session, length):
    initiative_id = 1
    response = await async_client.get(f"payments/initiative/{initiative_id}")
    assert response.status_code == 200
    assert len(response.json()["payments"]) == length


@pytest.mark.parametrize(
    "get_mock_user, start_date, end_date, min_amount, max_amount, route, expected_length, status_code",
    [
        (
            superuser,
            None,
            None,
            None,
            None,
            None,
            11,
            200,
        ),
        (
            superuser,
            "2023-08-15",
            "2023-10-03",
            None,
            None,
            None,
            10,
            200,
        ),
        (
            superuser,
            "2023-01-011",
            "2023-06-300",
            None,
            None,
            None,
            None,
            422,
        ),
        (
            superuser,
            None,
            None,
            0,
            700,
            None,
            8,
            200,
        ),
        (
            superuser,
            None,
            None,
            20.001,
            120.00,
            None,
            None,
            422,
        ),
        (
            superuser,
            None,
            None,
            None,
            None,
            "inkomen",
            6,
            200,
        ),
        (
            superuser,
            None,
            None,
            None,
            None,
            "onbekend",
            None,
            422,
        ),
        (superuser, "2000-08-15", "2023-10-03", 500.00, 100000, "uitgaven", 3, 200),
    ],
    ids=[
        "No filters returns all payments",
        "Date filter",
        "Invalid date returns error",
        "Transaction amount filter",
        "Invalid transaction amount returns error",
        "Route filter",
        "Invalid route returns error",
        "Filters can be combined",
    ],
    indirect=["get_mock_user"],
)
async def test_get_initiative_payments_filters(
    async_client,
    dummy_session,
    get_mock_user,
    start_date,
    end_date,
    min_amount,
    max_amount,
    route,
    expected_length,
    status_code,
):
    initiative_id = 1
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "min_amount": min_amount,
        "max_amount": max_amount,
        "route": route,
    }

    params = {k: v for k, v in params.items() if v is not None}

    response = await async_client.get(
        f"/payments/initiative/{initiative_id}", params=params
    )
    assert response.status_code == status_code
    if status_code == 200:
        payments = response.json()["payments"]
        assert len(payments) == expected_length
