import pytest
from sqlmodel import select
from open_poen_api.schemas_and_models.models import entities as e


@pytest.mark.parametrize(
    "auth, status_code",
    [
        ("admin_auth_2", 200),
        ("financial_auth_2", 200),
        ("initiative_owner_auth_2", 403),
        ("user_auth_2", 403),
        ("guest_auth_2", 401),
    ],
)
def test_post_initiative_payment(
    client,
    session_2,
    auth,
    status_code,
    payment_data,
    request,
):
    authorization_header, user_id, initiative_id, _ = request.getfixturevalue(auth)
    response = client.post(
        f"/initiative/{initiative_id}/payment",
        json=payment_data,
        headers=authorization_header,
    )
    assert response.status_code == status_code
