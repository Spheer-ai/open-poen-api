import pytest
from open_poen_api.bng import import_bng_payments
from open_poen_api.models import BNG
import pytest_asyncio
import json
from datetime import datetime
from pytz import UTC
from tests.conftest import superuser_info


@pytest_asyncio.fixture(scope="function")
async def bng_session(dummy_session):
    # One user and one bng account.
    with open("./tests/bng/bng_data.json", "r") as file:
        data = json.load(file)
    bng = BNG(
        iban=data["iban"],
        expires_on=datetime.fromisoformat(data["expires_on"]).replace(tzinfo=UTC),
        consent_id=data["consent_id"],
        access_token=data["access_token"],
        last_import_on=datetime.fromisoformat(data["last_import_on"]),
        user_id=data["user_id"],
    )
    dummy_session.add(bng)
    await dummy_session.commit()
    return dummy_session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user",
    [
        (superuser_info),
    ],
    indirect=["get_mock_user"],
)
async def test_import(async_client, bng_session):
    await import_bng_payments(bng_session)
