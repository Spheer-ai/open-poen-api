import pytest
from tests.conftest import user


@pytest.mark.parametrize(
    "get_mock_user, institution_id, n_days_access, n_days_history, expected_status_code",
    [
        (user, "SANDBOXFINANCE_SFIN0000", 10, 10, 200),
        (user, "INVALID_INSTITUTION", 10, 10, 400),
        (user, "SANDBOXFINANCE_SFIN0000", 91, 10, 400),
        (user, "SANDBOXFINANCE_SFIN0000", 0, 10, 400),
        (user, "SANDBOXFINANCE_SFIN0000", 10, 731, 400),
        (user, "SANDBOXFINANCE_SFIN0000", 10, 0, 400),
    ],
    ids=[
        "URL is returned for correct request",
        "Invalid institution_id returns 400",
        "n_days_access > 90 returns 400",
        "n_days_access < 1 returns 400",
        "n_days_history > 730 returns 400",
        "n_days_history < 1 returns 400",
    ],
    indirect=["get_mock_user"],
)
async def test_create_gocardless(
    async_client,
    dummy_session,
    get_mock_user,
    institution_id,
    n_days_access,
    n_days_history,
    expected_status_code,
):
    params = {
        "institution_id": institution_id,
        "n_days_access": n_days_access,
        "n_days_history": n_days_history,
    }
    user_id = 1
    response = await async_client.get(
        f"/users/{user_id}/gocardless-initiate", params=params
    )
    assert response.status_code == expected_status_code
    if expected_status_code == 200:
        assert "url" in response.json()


@pytest.mark.parametrize(
    "get_mock_user",
    [
        user,
    ],
    ids=[
        "Can get list of institutions",
    ],
    indirect=["get_mock_user"],
)
async def test_get_institutions(async_client, get_mock_user):
    response = await async_client.get("/utils/gocardless/institutions")
    assert any([i["id"] == "ING_INGBNL2A" for i in response.json()["institutions"]])
