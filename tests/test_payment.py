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
)


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
        (superuser, 409, 1, 1),
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
        (superuser, 409, 2, 1, 2),
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
