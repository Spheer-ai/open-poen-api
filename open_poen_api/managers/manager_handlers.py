from fastapi import UploadFile
from ..models import (
    ProfilePictureMixin,
    AttachmentEntityType,
    AttachmentAttachmentType,
    Attachment,
)
from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.utils import upload_profile_picture


T = TypeVar("T", bound=ProfilePictureMixin)


class ProfilePictureHandler(Generic[T]):
    def __init__(self, session: AsyncSession, entity_type: AttachmentEntityType):
        self.session = session
        self.entity_type = entity_type

    async def set_profile_picture(self, file: UploadFile, db_entity: T) -> None:
        filename = f"{db_entity.id}_{self.entity_type.value}_profile_picture"
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

        self.session.add(profile_picture)
        await self.session.commit()

    async def delete_profile_picture(self, db_entity: T) -> None:
        if db_entity.profile_picture is None:
            return

        await self.session.delete(db_entity.profile_picture)
        await self.session.commit()
