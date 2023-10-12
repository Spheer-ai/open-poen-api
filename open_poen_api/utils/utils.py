from fastapi import HTTPException, Request, UploadFile
from PIL import Image
import io
import os
import string
import random
import datetime
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from pydantic import BaseModel
from ..managers.exc import UnsupportedFileType, FileTooLarge

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
container_client = blob_service_client.get_container_client("media")


class ProfilePictureUpdate(BaseModel):
    raw_image_url: str | None
    raw_image_thumbnail_url: str | None


async def upload_profile_picture(
    file: UploadFile, filename: str
) -> ProfilePictureUpdate:
    if file.content_type not in ["image/png", "image/jpeg"]:
        raise UnsupportedFileType("Profile picture should be png or jpeg")

    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise FileTooLarge("Profile picture has a max size of 10 MB")

    ext = os.path.splitext(str(file.filename))[1][1:]
    original_blob_path = f"images/{filename}.{ext}"
    blob_client = container_client.get_blob_client(original_blob_path)
    await blob_client.upload_blob(file_content, overwrite=True)

    image = Image.open(io.BytesIO(file_content))
    image.thumbnail((1024, 1024))
    thumbnail_bytes = io.BytesIO()
    image_format = "PNG" if file.content_type == "image/png" else "JPEG"
    image.save(thumbnail_bytes, format=image_format)

    thumbnail_blob_path = f"image_thumbnails/thumbnail_{filename}.{ext}"
    thumbnail_blob_client = container_client.get_blob_client(thumbnail_blob_path)
    await thumbnail_blob_client.upload_blob(thumbnail_bytes.getvalue(), overwrite=True)

    return ProfilePictureUpdate(
        raw_image_url=blob_client.url,
        raw_image_thumbnail_url=thumbnail_blob_client.url,
    )


def generate_sas_token(blob_url: str) -> str:
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
