from fastapi import Request, UploadFile
from PIL import Image
import io
import os
import string
import random
import datetime
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import (
    BlobSasPermissions,
    generate_blob_sas,
    ContentSettings,
    PublicAccess,
)
from azure.core.exceptions import ResourceExistsError
from pydantic import BaseModel
from ..exc import FileTooLarge
from typing import TypeVar
import asyncio

DEBUG = os.environ.get("ENVIRONMENT") == "debug"


def get_requester_ip(request: Request):
    if request.client is not None:
        return request.client.host
    else:
        return "123.456.789.101"


def format_user_timestamp(user_id: int | None) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d:%H:%M:%S")
    formatted_string = f"{user_id}_{timestamp}"
    return formatted_string


def temp_password_generator(
    size: int = 10, chars=string.ascii_uppercase + string.digits
) -> str:
    if not DEBUG:
        return "".join(random.choice(chars) for _ in range(size))
    else:
        return "DEBUG_PASSWORD"


blob_service_client = BlobServiceClient.from_connection_string(
    os.environ["AZURE_STORAGE_CONNECTION_STRING"]
)
AZURE_STORAGE_ACCOUNT_KEY = os.environ["AZURE_STORAGE_ACCOUNT_KEY"]
container_client = blob_service_client.get_container_client(
    f"{os.environ['ENVIRONMENT']}-media"
)


async def create_media_container():
    # Only to be used locally when using azurite.
    if os.environ["ENVIRONMENT"] != "debug":
        raise ValueError("Can only create media container in debug mode")
    try:
        await blob_service_client.create_container(
            "debug-media", public_access=PublicAccess.CONTAINER
        )
    except ResourceExistsError:
        await blob_service_client.delete_container("debug-media")
        print("Media container deleted.")
        await blob_service_client.create_container(
            "debug-media", public_access=PublicAccess.CONTAINER
        )


class AttachmentUpdate(BaseModel):
    raw_attachment_url: str
    raw_attachment_thumbnail_128_url: str | None = None
    raw_attachment_thumbnail_256_url: str | None = None
    raw_attachment_thumbnail_512_url: str | None = None


async def upload_attachment(
    file: UploadFile, filename: str, make_thumbnail=True
) -> AttachmentUpdate:
    if file.content_type not in ("image/png", "image/jpeg") and make_thumbnail:
        raise ValueError("Can only make thumbnails for png and jpeg")

    # TODO: Verify that the mime type is correct by checking the first n bytes.
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise FileTooLarge("Maximum file size of any upload 10 MB")

    ext = os.path.splitext(str(file.filename))[1][1:]
    original_blob_path = f"images/{filename}.{ext}"
    # TODO: do not save the the entire blob path, because then we can't easily azcopy
    # data from azure to Azurite locally and test there.
    blob_client = container_client.get_blob_client(original_blob_path)
    await blob_client.upload_blob(
        file_content,
        overwrite=True,
        content_settings=ContentSettings(content_type=file.content_type),
    )

    if not make_thumbnail:
        return AttachmentUpdate(raw_attachment_url=blob_client.url)

    image = Image.open(io.BytesIO(file_content))
    image_format = "PNG" if file.content_type == "image/png" else "JPEG"

    thumbnail_urls = {}

    for size in [128, 256, 512]:
        thumbnail = image.copy()
        thumbnail.thumbnail((size, size))

        thumbnail_bytes = io.BytesIO()
        thumbnail.save(thumbnail_bytes, format=image_format)

        thumbnail_blob_path = f"image_thumbnails/{filename}_{size}.{ext}"
        thumbnail_blob_client = container_client.get_blob_client(thumbnail_blob_path)
        await thumbnail_blob_client.upload_blob(
            thumbnail_bytes.getvalue(),
            overwrite=True,
            content_settings=ContentSettings(content_type=file.content_type),
        )
        thumbnail_urls[size] = thumbnail_blob_client.url

    return AttachmentUpdate(
        raw_attachment_url=blob_client.url,
        raw_attachment_thumbnail_128_url=thumbnail_urls[128],
        raw_attachment_thumbnail_256_url=thumbnail_urls[256],
        raw_attachment_thumbnail_512_url=thumbnail_urls[512],
    )


T = TypeVar("T", str, None)


def generate_sas_token(blob_url: T) -> T:
    if blob_url is None:
        return blob_url

    if os.environ["ENVIRONMENT"] == "debug":
        return blob_url.replace("azurite", "localhost")

    url_parts = blob_url.split("/")
    account_name = url_parts[2].split(".")[0]
    container_name = url_parts[3]
    blob_name = "/".join(url_parts[4:])

    sas_permissions = BlobSasPermissions(read=True)
    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=sas_permissions,
        expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    )
    return f"{blob_url}?{sas_token}"
