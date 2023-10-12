import pytest
from open_poen_api.models import User
from tests.conftest import (
    superuser,
    userowner,
    user,
    anon,
)
import asyncio
from fastapi import UploadFile
from io import BytesIO


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_mock_user, file_name, status_code",
    [
        (superuser, "./tests/dummy_data/test.png", 200),
    ],
    ids=[
        "Superuser can upload",
    ],
    indirect=["get_mock_user"],
)
async def test_upload_files(
    async_client,
    dummy_session,
    status_code,
    file_name,
):
    with open(file_name, "rb") as f:
        file_content = f.read()

    files = [("files", ("name.png", file_content, "image/png"))]

    response = await async_client.post(
        f"/user/1/upload-files/profile_picture",
        files=files,
    )

    assert response.status_code == status_code
    if status_code == 200:
        db_user = await dummy_session.get(User, 1)
        assert db_user.image_path is not None
        assert db_user.image_thumbnail_path is not None
