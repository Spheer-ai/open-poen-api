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
    bankaccount_owner,
    payment_info,
    policy_officer,
)
from open_poen_api.models import Payment, Initiative
from decimal import Decimal


@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser, 200), (admin, 200), (user, 403), (grant_officer, 403), (anon, 403)],
    ids=[
        "Superuser can",
        "Administrator can",
        "User cannot",
        "Grant officer cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_create_payment(async_client, dummy_session, status_code):
    body = payment_info
    response = await async_client.post("/payment", json=body)
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "get_mock_user, status_code, payment_id",
    [
        (superuser, 204, 1),
        (admin, 204, 1),
        (user, 403, 1),
        (grant_officer, 403, 1),
        (anon, 403, 1),
        (superuser, 403, 2),
    ],
    ids=[
        "Superuser can",
        "Administrator can",
        "User cannot",
        "Grant officer cannot",
        "Anon cannot",
        "GoCardless cannot be deleted",
    ],
    indirect=["get_mock_user"],
)
async def test_delete_payment(async_client, dummy_session, status_code, payment_id):
    response = await async_client.delete(f"/payment/{payment_id}")
    assert response.status_code == status_code


@pytest.mark.parametrize(
    "get_mock_user, body, status_code, payment_id",
    [
        (superuser, {"short_user_description": "test"}, 200, 1),
        (superuser, {"short_user_description": "test"}, 200, 2),
        (grant_officer, {"short_user_description": "test"}, 200, 1),
        (superuser, {"debtor_account": "AB1234"}, 200, 1),
        (superuser, {"debtor_account": "AB1234"}, 403, 2),
        (policy_officer, {"short_user_description": "test"}, 403, 1),
        (user, {"short_user_description": "test"}, 403, 1),
        (bankaccount_owner, {"short_user_description": "test"}, 403, 5),
        (initiative_owner, {"short_user_description": "test"}, 200, 14),
        (activity_owner, {"short_user_description": "test"}, 200, 15),
        (activity_owner, {"short_user_description": "test"}, 403, 1),
    ],
    ids=[
        "Superuser can edit description on manual",
        "Superuser can edit description on GoCardless",
        "Grant officer can edit description on manual",
        "Superuser can edit debtor_account on manual",
        "Superuser cannot edit debtor_account on GoCardless",
        "Policy officer cannot edit at all",
        "User cannot cannot edit at all",
        "Bank account owner cannot edit at all if not initiative owner as well",
        "Initiative owner can edit if payment is in initiative",
        "Activity owner can edit if payment is in activity",
        "Activity owner cannot edit if payment is in initiative but not activity",
    ],
    indirect=["get_mock_user"],
)
async def test_patch_payment(
    async_client, dummy_session, body, status_code, payment_id
):
    response = await async_client.patch(f"/payment/{payment_id}", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        funder = await dummy_session.get(Payment, payment_id)
        for key in body:
            assert getattr(funder, key) == body[key]


@pytest.mark.parametrize(
    "get_mock_user, status_code, hidden_present, payment_id, n_attachments",
    [
        (superuser, 200, True, 15, 1),
        (user, 403, False, 15, 1),
        (user, 200, False, 13, 0),
    ],
    ids=[
        "Superuser can see hidden payment with hidden field",
        "User cannot see hidden payment",
        "User can see public payment without hidden field",
    ],
    indirect=["get_mock_user"],
)
async def test_get_linked_payment_detail(
    async_client, dummy_session, status_code, hidden_present, payment_id, n_attachments
):
    response = await async_client.get(f"/payment/{payment_id}")
    assert response.status_code == status_code
    if status_code == 200:
        if hidden_present:
            assert "hidden" in response.json()
        assert len(response.json()["attachments"]) == n_attachments


@pytest.mark.parametrize(
    "get_mock_user, status_code, length",
    [(initiative_owner, 200, 1), (activity_owner, 200, 1), (user, 200, 0)],
    ids=[
        "Initiative owner gets his initiatives",
        "Activity owner gets initiatives of activities",
        "User without initiatives gets empty list",
    ],
    indirect=["get_mock_user"],
)
async def test_get_linkable_initiatives(
    async_client, dummy_session, status_code, length
):
    response = await async_client.get("/auth/entity-access/linkable-initiatives")
    assert response.status_code == status_code
    assert len(response.json()["initiatives"]) == length


@pytest.mark.parametrize(
    "get_mock_user, status_code, length",
    [(initiative_owner, 200, 2), (activity_owner, 200, 1), (user, 200, 0)],
    ids=[
        "Initiative owner gets his activities",
        "Activity owner gets his activities",
        "User without initiatives gets empty list",
    ],
    indirect=["get_mock_user"],
)
async def test_get_linkable_activities(
    async_client, dummy_session, status_code, length
):
    initiative_id = 1
    response = await async_client.get(
        f"/auth/entity-access/initiative/{initiative_id}/linkable-activities"
    )
    assert response.status_code == status_code
    assert len(response.json()["activities"]) == length


@pytest.mark.parametrize(
    "get_mock_user, status_code, payment_id, initiative_id",
    [
        (superuser, 403, 1, 1),
        (superuser, 200, 5, 1),
        (superuser, 200, 6, 2),
        (superuser, 200, 6, None),
        (user, 403, 5, 1),
        (initiative_owner, 403, 5, 1),
        (grant_officer, 403, 5, 1),
        (admin, 200, 5, 1),
        (bankaccount_owner, 200, 6, None),
    ],
    ids=[
        "Payment cannot link to initiative with activity set",
        "Payment can link to initiative with activity not set",
        "Payment only linked to initiative can be set to other initiative",
        "Payment only linked to initiative can be removed from initiative",
        "User cannot link",
        "Initiative owner cannot link if not owner on bank account or payment not under his initiative",
        "Grant officer cannot link if not owner on bank account or payment not under his regulation",
        "Administrator can link because can edit all initiatives and payments",
        "Bank account owner can detach his own payment from initiative that is not his",
    ],
    indirect=["get_mock_user"],
)
async def test_switch_initiative(
    async_client, dummy_session, status_code, payment_id, initiative_id
):
    body = {"initiative_id": initiative_id}
    response = await async_client.patch(
        f"/payment/{payment_id}/initiative",
        json=body,
    )
    assert response.status_code == status_code
    if response.status_code == 409:
        assert (
            response.json()
            == "Payment is still linked to an activity. First decouple it."
        )


@pytest.mark.parametrize(
    "get_mock_user, status_code, payment_id, activity_id, initiative_id",
    [
        (superuser, 403, 2, 1, 2),
        (superuser, 200, 6, 1, 1),
        (superuser, 200, 1, 1, 1),
        (superuser, 200, 1, None, 1),
        (initiative_owner, 200, 6, 1, 1),
        (activity_owner, 403, 6, 1, 1),
    ],
    ids=[
        "Payment cannot link to activity with initiative not set",
        "Payment can link to activity with initiative set",
        "Payment already linked to activity can be set to other activity",
        "Payment already linked to activity can be uncoupled from activity",
        "Initiative owner can link payment in his initiative to activity in initiative",
        "Activity owner cannot link payment to his activity from other activity that is not his",
    ],
    indirect=["get_mock_user"],
)
async def test_switch_activity(
    async_client, dummy_session, status_code, payment_id, activity_id, initiative_id
):
    body = {"activity_id": activity_id, "initiative_id": initiative_id}
    response = await async_client.patch(
        f"/payment/{payment_id}/activity",
        json=body,
    )
    assert response.status_code == status_code
    if response.status_code == 409:
        assert (
            response.json()
            == "Payment is not linked to an initiative. First couple it."
        )


@pytest.mark.parametrize(
    "get_mock_user, status_code, payment_id, initiative_id",
    [
        (superuser, 200, 6, None),
    ],
    ids=[
        "Initiative aggregates are updated when payment is unlinked from it",
    ],
    indirect=["get_mock_user"],
)
async def test_initiative_budget_update(
    async_client, dummy_session, status_code, payment_id, initiative_id
):
    body = {"initiative_id": initiative_id}
    response = await async_client.patch(
        f"/payment/{payment_id}/initiative",
        json=body,
    )
    assert response.status_code == status_code
    initiative = await dummy_session.get(Initiative, 1)

    # Hardcoded: current expenses of initiative minus payment amount.
    should_be = Decimal("2827.44") - Decimal("150.75")

    assert initiative.expenses == should_be

    print("stop")
