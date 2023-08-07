import pytest
from tests.conftest import (
    superuser_info,
    user_info,
    admin_info,
    anon_info,
    funder_info,
)
from open_poen_api.models import Funder


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 200), (user_info, 403), (admin_info, 200), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_create_funder(async_client, dummy_session, status_code):
    body = funder_info
    response = await async_client.post("/funder", json=body)
    assert response.status_code == status_code
    if status_code == 200:
        db_funder = dummy_session.get(Funder, response.json()["id"])
        assert db_funder is not None
        funder_data = response.json()
        assert funder_data["name"] == body["name"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, status_code",
    [(superuser_info, 204), (user_info, 403), (admin_info, 204), (anon_info, 403)],
    ids=["Superuser can", "User cannot", "Administrator can", "Anon cannot"],
    indirect=["get_mock_user"],
)
async def test_delete_funder(async_client, dummy_session, status_code):
    funder_id = 1
    response = await async_client.delete(f"/funder/{funder_id}")
    assert response.status_code == status_code
    if status_code == 204:
        funder = await dummy_session.get(Funder, funder_id)
        assert funder is None
