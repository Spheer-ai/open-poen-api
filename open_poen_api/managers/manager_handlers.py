from fastapi import UploadFile, HTTPException, Depends, Request
from PIL import Image
from azure.storage.blob.aio import BlobServiceClient
import os
import io
from fastapi_users.schemas import CreateUpdateDictModel
from pydantic import EmailStr, BaseModel

# from .user_manager import UserManager
# from .base_manager_ex_current_user import BaseManagerExCurrentUser
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Protocol
from ..models import Base, User

# T = TypeVar("T", bound=Base)


blob_service_client = BlobServiceClient.from_connection_string(
    os.environ["AZURE_STORAGE_CONNECTION_STRING"]
)
container_client = blob_service_client.get_container_client("media")


class ProfilePictureUpdate(CreateUpdateDictModel):
    image_path: str | None
    image_thumbnail_path: str | None
    # To match the type on BaseUserUpdate. The update method on the user manager
    # accepts only this type. These None values are not set in the db unless passed
    # on instantiation.
    # password: str | None = None
    # email: EmailStr | None = None
    # is_active: bool | None = None
    # is_superuser: bool | None = None
    # is_verified: bool | None = None


async def upload_profile_picture(
    file: UploadFile, filename: str
) -> ProfilePictureUpdate:
    if file.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File larger than 10MB")

    ext = os.path.splitext(str(file.filename))[1]
    original_blob_path = f"images/{filename}.{ext}"
    blob_client = container_client.get_blob_client(original_blob_path)
    await blob_client.upload_blob(file_content)

    image = Image.open(io.BytesIO(file_content))
    image.thumbnail((128, 128))
    thumbnail_bytes = io.BytesIO()
    image_format = "PNG" if file.content_type == "image/png" else "JPEG"
    image.save(thumbnail_bytes, format=image_format)

    thumbnail_blob_path = f"image_thumbnails/thumbnail_{filename}.{ext}"
    thumbnail_blob_client = container_client.get_blob_client(thumbnail_blob_path)
    await thumbnail_blob_client.upload_blob(thumbnail_bytes.getvalue())

    return ProfilePictureUpdate(
        image_path=original_blob_path, image_thumbnail_path=thumbnail_blob_path
    )


# async def set_profile_picture(file: UploadFile, instance: Base) -> None:
#     filename = f"{instance.id}_{instance.__class__.__name__}_profile_picture"
#     await upload_profile_picture(file, filename)


# async def unset_profile_picture(instance: Base) -> None:
#     instance.image_path = None
#     instance.image_thumbnail_path = None


# class UserProfilePictureUploadHandler:
#     def __init__(self, user_manager: UserManager = Depends(UserManager)):
#         self.manager = user_manager

#     async def set_profile_picture(self, file: UploadFile, instance: User) -> None:
#         filename = f"{instance.id}_user_profile_picture"
#         profile_picture_update = await upload_profile_picture(file, filename)
#         await self.manager.update(profile_picture_update, instance, request=None)

#     async def unset_profile_picture(self, instance: User) -> None:
#         # user.image_path = None
#         # user.image_thumbnail_path = None
#         pass
