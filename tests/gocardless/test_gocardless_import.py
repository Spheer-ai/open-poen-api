# import pytest
# from open_poen_api.schemas_and_models.models import entities as ent
# from tests.conftest import superuser_info


# @pytest.mark.parametrize(
#     "get_mock_user",
#     [superuser_info],
#     indirect=["get_mock_user"],
# )
# async def test_import(async_client, as_1):
#     requisition = await as_1.get(ent.Requisition, 1)
#     if requisition is None:
#         return
