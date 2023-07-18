from datetime import datetime, timedelta
import pytest
from tests.conftest import superuser_info


param_combs = [
    (
        "NL34BNGT5532530633",
        (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        True,
    ),
    ("INVALID-IBAN", (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"), False),
    (
        "NL34BNGT5532530633",
        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        False,
    ),
]


@pytest.mark.parametrize("iban,expires_on,should_return_200", param_combs)
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200)],
    indirect=["get_mock_user"],
)
async def test_create_bng(
    iban, expires_on, should_return_200, async_client, as_1, status_code
):
    params = {
        "iban": iban,
        "expires_on": expires_on,
    }
    user_id = 1
    response = await async_client.get(f"/users/{user_id}/bng-initiate", params=params)
    if should_return_200 and status_code == 200:
        assert response.status_code == 200
        assert "url" in response.json()
    else:
        assert response.status_code == 400
