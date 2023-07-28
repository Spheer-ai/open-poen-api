import pytest
from open_poen_api.bng import get_bng_payments
from open_poen_api.schemas_and_models.models.entities import BNG
import pytest_asyncio
import json
from datetime import datetime
from pytz import UTC
from tests.conftest import superuser_info


@pytest_asyncio.fixture(scope="function")
async def as_with_bng_account(as_1):
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
    as_1.add(bng)
    await as_1.commit()
    return as_1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user",
    [
        (superuser_info),
    ],
    indirect=["get_mock_user"],
)
async def test_import(async_client, as_with_bng_account):
    await get_bng_payments(as_with_bng_account)
