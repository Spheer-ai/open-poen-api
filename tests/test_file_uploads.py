import pytest
from open_poen_api.models import User, Initiative
from tests.conftest import userowner, initiative_owner
import asyncio
from fastapi import UploadFile
from io import BytesIO
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


@pytest.mark.parametrize(
    "get_mock_user, file_name, status_code",
    [
        (userowner, "./tests/dummy_data/test.png", 200),
    ],
    ids=[
        "User owner can upload",
    ],
    indirect=["get_mock_user"],
)
async def test_upload_profile_picture_user(
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
        q = await dummy_session.get(User, 1)
        r = q.profile_picture
        assert r.attachment_url is not None
        assert r.attachment_thumbnail_url_128 is not None
        assert r.attachment_thumbnail_url_256 is not None
        assert r.attachment_thumbnail_url_512 is not None

    response = await async_client.delete(f"/user/1/profile-picture")

    assert response.status_code == 204
    if response.status_code == 204:
        q = await dummy_session.get(User, 1)
        await dummy_session.refresh(q)
        r = q.profile_picture
        assert r is None


@pytest.mark.parametrize(
    "get_mock_user, file_name, status_code",
    [
        (initiative_owner, "./tests/dummy_data/test.png", 200),
    ],
    ids=[
        "Initiative owner can upload",
    ],
    indirect=["get_mock_user"],
)
async def test_upload_profile_picture_initiative(
    async_client,
    dummy_session,
    status_code,
    file_name,
):
    with open(file_name, "rb") as f:
        file_content = f.read()

    files = [("file", ("name.png", file_content, "image/png"))]

    response = await async_client.post(
        f"/initiative/1/profile-picture",
        files=files,
    )

    assert response.status_code == status_code
    if status_code == 200:
        q = (
            select(Initiative)
            .options(joinedload(Initiative.profile_picture))
            .where(Initiative.id == 1)
        )
        q = await dummy_session.execute(q)
        q = q.scalars().first()
        r = q.profile_picture
        assert r.attachment_url is not None
        assert r.attachment_thumbnail_url_128 is not None
        assert r.attachment_thumbnail_url_256 is not None
        assert r.attachment_thumbnail_url_512 is not None

    response = await async_client.delete(f"/initiative/1/profile-picture")

    assert response.status_code == 204
    if response.status_code == 204:
        q = (
            select(Initiative)
            .options(joinedload(Initiative.profile_picture))
            .where(Initiative.id == 1)
        )
        q = await dummy_session.execute(q)
        q = q.scalars().first()
        r = q.profile_picture
        await dummy_session.refresh(q)
        r = q.profile_picture
        assert r is None
