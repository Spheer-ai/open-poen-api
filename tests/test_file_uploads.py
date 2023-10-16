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

    files = [("file", ("name.png", file_content, "image/png"))]

    response = await async_client.post(
        f"/user/1/profile-picture",
        files=files,
    )

    assert response.status_code == status_code
    if status_code == 200:
        # db_user = await dummy_session.get(User, 1)
        # assert db_user.image_url is not None
        # assert db_user.image_thumbnail_url is not None
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        q = await dummy_session.execute(
            select(User).options(selectinload(User.profile_picture))
        )
        r = q.scalars().first()
        print("stop")
