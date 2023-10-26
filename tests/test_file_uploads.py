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
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


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
        f"/user/6/profile-picture",
        files=files,
    )

    assert response.status_code == status_code
    if status_code == 200:
        q = await dummy_session.execute(
            select(User).options(joinedload(User.profile_picture))
        )
        r = q.scalars().first().profile_picture
        assert r.attachment_url is not None
        assert r.attachment_thumbnail_url_128 is not None
        assert r.attachment_thumbnail_url_256 is not None
        assert r.attachment_thumbnail_url_512 is not None

    response = await async_client.delete(f"/user/1/profile-picture/{r.id}")

    assert response.status_code == 204
    if response.status_code == 204:
        q = await dummy_session.execute(
            select(User).options(joinedload(User.profile_picture))
        )
        r = q.scalars().first().profile_picture
        assert r is None
