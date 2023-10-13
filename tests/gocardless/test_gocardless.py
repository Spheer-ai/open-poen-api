# import pytest
# from tests.conftest import user_info


# @pytest.mark.parametrize(
#     "get_mock_user, status_code",
#     [(user_info, 200)],
#     indirect=["get_mock_user"],
# )
# async def test_create_gocardless(async_client, as_1, status_code):
#     params = {"institution_id": "ING_INGBNL2A"}
#     user_id = 1
#     response = await async_client.get(
#         f"/users/{user_id}/gocardless-initiate", params=params
#     )
#     assert response.status_code == status_code


# @pytest.fixture(scope="module")
# def token() -> gcl.Token:
#     return gcl.create_new_token()


# @pytest.fixture(scope="module")
# def institutions(token) -> list[gcl.Institution]:
#     return gcl.get_institutions(access_token=token.access)


# def test_create_new_token():
#     token = gcl.create_new_token()


# def test_get_institutions(token):
#     gcl.get_institutions(access_token=token.access)


# def test_create_new_agreement(token, institutions):
#     ing = [i for i in institutions if i.name == "ING"][0]
#     gcl.create_new_agreement(access_token=token.access, institution=ing)
