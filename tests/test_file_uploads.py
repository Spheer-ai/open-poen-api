import pytest
from open_poen_api.models import User, Initiative, Payment
from tests.conftest import userowner, initiative_owner, user, superuser
import asyncio
from fastapi import UploadFile
from io import BytesIO
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload


def file_content():
    file_path = "./tests/dummy_data/test.png"
    with open(file_path, "rb") as f:
        return f.read()


async def assert_profile_picture(
    dummy_session, entity_class, entity_id, should_be_present
):
    q = await dummy_session.get(entity_class, entity_id, populate_existing=True)
    if should_be_present:
        assert q.profile_picture is not None
        assert q.profile_picture.attachment_url is not None
        assert q.profile_picture.attachment_thumbnail_url_128 is not None
        assert q.profile_picture.attachment_thumbnail_url_256 is not None
        assert q.profile_picture.attachment_thumbnail_url_512 is not None
    else:
        assert q.profile_picture is None


@pytest.mark.parametrize(
    "get_mock_user, entity_type, entity_id, status_code",
    [
        (userowner, User, 1, 200),
        (user, User, 1, 403),
        (initiative_owner, Initiative, 1, 200),
        (user, Initiative, 1, 403),
    ],
    ids=[
        "User owner can upload own profile picture",
        "User cannot upload profile picture of other user",
        "Initiative owner can upload own initiative's profile picture",
        "User cannot upload profile picture of other initiative",
    ],
    indirect=["get_mock_user"],
)
async def test_upload_profile_picture(
    async_client,
    dummy_session,
    get_mock_user,
    entity_type,
    entity_id,
    status_code,
):
    files = [("file", ("name.png", file_content(), "image/png"))]
    response = await async_client.post(
        f"/{entity_type.__name__.lower()}/{entity_id}/profile-picture", files=files
    )

    assert response.status_code == status_code

    if status_code == 403:
        # Other asserts don't make sense if the profile picture can't be set.
        return

    await assert_profile_picture(
        dummy_session, entity_type, entity_id, should_be_present=True
    )

    response = await async_client.delete(
        f"/{entity_type.__name__.lower()}/{entity_id}/profile-picture"
    )
    assert response.status_code == 204
    await assert_profile_picture(
        dummy_session, entity_type, entity_id, should_be_present=False
    )


@pytest.mark.parametrize(
    "get_mock_user, status_code, n_added",
    [(superuser, 200, 0), (superuser, 200, 1)],
    ids=[
        "Super user can upload single attachment",
        "Super user can upload multiple attachments",
    ],
    indirect=["get_mock_user"],
)
async def test_upload_attachment(
    async_client, dummy_session, get_mock_user, status_code, n_added
):
    files = [("files", ("name.png", file_content(), "image/png"))]
    for i in range(0, n_added):
        files += [("files", ("name.png", file_content(), "image/png"))]
    payment_id = 1
    response = await async_client.post(
        f"/payment/{payment_id}/attachments", files=files
    )

    assert response.status_code == status_code

    if status_code == 200:
        q = await dummy_session.execute(
            select(Payment)
            .options(selectinload(Payment.attachments))
            .where(Payment.id == payment_id)
        )
        r = q.scalars().first()
        assert len(r.attachments) == n_added + 1
