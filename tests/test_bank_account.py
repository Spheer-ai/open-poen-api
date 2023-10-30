import pytest
from tests.conftest import (
    superuser,
    userowner,
    grant_officer,
    user,
    anon,
)


@pytest.mark.parametrize(
    "get_mock_user, status_code, fields_present, fields_not_present",
    [
        (
            userowner,
            200,
            ["owner", "name", "iban", "expiration_date"],
            ["api_account_id"],
        ),
        (user, 403, [], []),
        (grant_officer, 403, [], []),
        (anon, 403, [], []),
    ],
    ids=[
        "User owner sees everything except api id",
        "User cannot",
        "Grant officer cannot",
        "Anon cannot",
    ],
    indirect=["get_mock_user"],
)
async def test_get_bank_account_detail(
    async_client, dummy_session, status_code, fields_present, fields_not_present
):
    user_id, bank_account_id = 1, 1
    response = await async_client.get(f"/user/{user_id}/bank-account/{bank_account_id}")
    assert response.status_code == status_code
    assert all([i in response.json() for i in fields_present])
    assert all([i not in response.json() for i in fields_not_present])


# @pytest.mark.parametrize(
#     "get_mock_user",
#     [userowner],
#     ids=[
#         "User owner can finish",
#     ],
#     indirect=["get_mock_user"],
# )
# async def test_finish_bank_account(async_client, dummy_session):
#     user_id, bank_account_id = 1, 1
#     response = await async_client.patch(
#         f"/user/{user_id}/bank-account/{bank_account_id}"
#     )
