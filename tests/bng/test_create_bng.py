from datetime import datetime, timedelta
import pytest


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
async def test_create_bng(
    iban,
    expires_on,
    should_return_200,
    async_client,
    async_session,
    user_created_by_admin,
):
    params = {
        "iban": iban,
        "expires_on": expires_on,
    }
    user_id = 1
    response = await async_client.get(f"/users/{user_id}/bng-initiate", params=params)
    if should_return_200:
        assert response.status_code == 200
        assert "url" in response.json()
    else:
        assert response.status_code == 400
