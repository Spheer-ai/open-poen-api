from fastapi import HTTPException, Request, UploadFile
from PIL import Image
import io
import os
import string
import random
import datetime
from azure.storage.blob.aio import BlobServiceClient
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
container_client = blob_service_client.get_container_client("media")


class ProfilePictureUpdate(BaseModel):
    image_path: str | None
    image_thumbnail_path: str | None


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
        image_path=blob_client.url, image_thumbnail_path=thumbnail_blob_client.url
    )
