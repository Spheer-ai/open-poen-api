import pytest
from sqlmodel import select
from open_poen_api.schemas_and_models.models import entities as ent


@pytest.mark.parametrize(
    "auth, status_code",
    [
        ("init_admin_3", 200),
        ("init_financial_3", 200),
        ("init_initiative_owner_3", 403),
        ("init_activity_owner_3", 403),
        ("init_user_3", 403),
        ("init_guest_3", 401),
    ],
)
def test_post_initiative_payment(
    client,
    auth,
    status_code,
    payment_data,
    request,
):
    authorization_header, initiative_id, _ = request.getfixturevalue(auth)
    response = client.post(
        f"/initiative/{initiative_id}/payment",
        json=payment_data,
        headers=authorization_header,
    )
    assert response.status_code == status_code


# auth_data = {
#     "init_admin_3": {"short_user_description": 200, "hidden": 200, "debtor_name": 200},
#     "init_financial_3": {
#         "short_user_description": 200,
#         "hidden": 200,
#         "debtor_name": 200,
#     },
#     "init_initiative_owner_3": {
#         "short_user_description": 200,
#         "hidden": 200,
#         "debtor_name": 403,
#     },
#     "init_activity_owner_3": {
#         "short_user_description": 200,
#         "hidden": 403,
#         "debtor_name": 403,
#     },
#     "init_user_3": {"short_user_description": 403, "hidden": 403, "debtor_name": 403},
#     "init_guest_3": {"short_user_description": 401, "hidden": 401, "debtor_name": 401},
# }

# payment_data_set = [
#     {
#         "short_user_description": "Updated Description",
#         "hidden": True,
#         "debtor_name": "Updated Debtor",
#     }
# ]

combinations = [
    ("init_admin_3", {"short_user_description": "Updated Description"}, 200),
    ("init_admin_3", {"hidden": True}, 200),
    ("init_admin_3", {"debtor_name": "Updated Name"}, 200),
    ("init_financial_3", {"short_user_description": "Updated Description"}, 200),
    ("init_financial_3", {"hidden": True}, 200),
    ("init_financial_3", {"debtor_name": "Updated Name"}, 200),
    ("init_initiative_owner_3", {"short_user_description": "Updated Description"}, 200),
    ("init_initiative_owner_3", {"hidden": True}, 200),
    ("init_initiative_owner_3", {"debtor_name": "Updated Name"}, 403),
    ("init_activity_owner_3", {"short_user_description": "Updated Description"}, 403),
    ("init_activity_owner_3", {"hidden": True}, 403),
    ("init_activity_owner_3", {"debtor_name": "Updated Name"}, 403),
    ("init_guest_3", {"debtor_name": "Updated Name"}, 401),
]


@pytest.mark.parametrize("comb", combinations)
def test_patch_initiative_payment(client, request, comb):
    auth, payment_data, status_code = comb
    (
        authorization_header,
        initiative_id,
        activity_id,
    ) = request.getfixturevalue(auth)

    response = client.patch(
        f"/initiative/{initiative_id}/payment/1",
        json=payment_data,
        headers=authorization_header,
    )
    assert response.status_code == status_code
    if status_code == 200:
        key = list(payment_data.keys())[0]
        value = list(payment_data.values())[0]
        assert response.json()[key] == value
