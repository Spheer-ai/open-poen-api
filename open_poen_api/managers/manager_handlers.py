from fastapi import UploadFile, Request
from ..models import (
    ProfilePictureMixin,
    AttachmentEntityType,
    AttachmentAttachmentType,
    Attachment,
    User,
)
from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.utils import upload_profile_picture
from .base_manager import BaseManager
import datetime


T = TypeVar("T", bound=ProfilePictureMixin)


class ProfilePictureHandler(BaseManager, Generic[T]):
    def __init__(
        self,
        session: AsyncSession,
        current_user: User | None,
        entity_type: AttachmentEntityType,
    ):
        super().__init__(session, current_user)
        self.entity_type = entity_type

    async def set(self, file: UploadFile, db_entity: T, request: Request) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = (
            f"{db_entity.id}_{self.entity_type.value}_profile_picture_{timestamp}"
        )
        ppu = await upload_profile_picture(file, filename)
        if db_entity.profile_picture is None:
            profile_picture = Attachment(
                entity_id=db_entity.id,
                entity_type=self.entity_type,
                attachment_type=AttachmentAttachmentType.PROFILE_PICTURE,
            )
        else:
            profile_picture = db_entity.profile_picture

        profile_picture.raw_attachment_url = ppu.raw_attachment_url
        profile_picture.raw_attachment_thumbnail_128_url = (
            ppu.raw_attachment_thumbnail_128_url
        )
        profile_picture.raw_attachment_thumbnail_256_url = (
            ppu.raw_attachment_thumbnail_256_url
        )
        profile_picture.raw_attachment_thumbnail_512_url = (
            ppu.raw_attachment_thumbnail_512_url
        )

        self.crud.session.add(profile_picture)
        await self.crud.session.commit()
        await self.crud.after_update(
            db_entity, {"profile_picture": "created"}, request=request
        )

    async def delete(self, db_entity: T, request: Request) -> None:
        if db_entity.profile_picture is None:
            return

        await self.crud.session.delete(db_entity.profile_picture)
        await self.crud.session.commit()
        await self.crud.after_update(
            db_entity, {"profile_picture": "created"}, request=request
        )
