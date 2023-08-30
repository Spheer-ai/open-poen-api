import pytest
from tests.conftest import (
    superuser,
    initiative_owner,
    user,
    admin,
    anon,
    initiative_info,
    policy_officer,
)
from open_poen_api.models import Initiative, Payment, Route, PaymentType
from open_poen_api.managers import get_initiative_manager
from decimal import Decimal
from datetime import datetime


dummy_payments = [
    {
        "transaction_id": "txn_0001",
        "booking_date": datetime.now(),
        "route": Route.INCOME,
        "type": PaymentType.BNG,
        "transaction_amount": Decimal("100.00"),
        "initiative_id": 1,
        "activity_id": None,
    },
    {
        "transaction_id": "txn_0002",
        "booking_date": datetime.now(),
        "route": Route.EXPENSES,
        "type": PaymentType.GOCARDLESS,
        "transaction_amount": Decimal("50.00"),
        "initiative_id": 1,
        "activity_id": None,
    },
    {
        "transaction_id": "txn_0003",
        "booking_date": datetime.now(),
        "route": Route.INCOME,
        "type": PaymentType.MANUAL,
        "transaction_amount": Decimal("200.00"),
        "initiative_id": 1,
        "activity_id": None,
    },
    {
        "transaction_id": "txn_0004",
        "booking_date": datetime.now(),
        "route": Route.EXPENSES,
        "type": PaymentType.BNG,
        "transaction_amount": Decimal("25.00"),
        "initiative_id": 1,
        "activity_id": 1,
    },
    {
        "transaction_id": "txn_0005",
        "booking_date": datetime.now(),
        "route": Route.INCOME,
        "type": PaymentType.GOCARDLESS,
        "transaction_amount": Decimal("150.00"),
        "initiative_id": 1,
        "activity_id": 1,
    },
]

# To use the dicts to create instances of Payment
# dummy_payment_instances = [Payment(**data) for data in dummy_payments]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [
        (superuser, 200),
    ],
    ids=[
        "Superuser can",
    ],
    indirect=["get_mock_user"],
)
async def test_financial_summary(async_client, dummy_session, status_code):
    payments = [Payment(**i) for i in dummy_payments]
    dummy_session.add_all(payments)
    await dummy_session.commit()

    initiative_id = 1
    response = await async_client.get(f"/initiative/{initiative_id}")
    assert response.status_code == status_code
    if status_code == 200:
        db_initiative = dummy_session.get(Initiative, response.json()["id"])
        assert db_initiative is not None
        initiative_data = response.json()
        assert initiative_data["name"] == body["name"]
