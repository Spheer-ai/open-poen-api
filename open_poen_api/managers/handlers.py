from fastapi import UploadFile, Request
from ..models import (
    ProfilePictureMixin,
    AttachmentEntityType,
    AttachmentAttachmentType,
    Attachment,
    User,
    AttachmentMixin,
)
from typing import TypeVar, Generic
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.utils import upload_attachment, AttachmentUpdate
from .base_manager import BaseManager
import datetime
from ..exc import EntityNotFound, UnsupportedFileType, FileTooLarge


def assign_attachment_urls(entity: Attachment, au: AttachmentUpdate):
    entity.raw_attachment_url = au.raw_attachment_url
    entity.raw_attachment_thumbnail_128_url = au.raw_attachment_thumbnail_128_url
    entity.raw_attachment_thumbnail_256_url = au.raw_attachment_thumbnail_256_url
    entity.raw_attachment_thumbnail_512_url = au.raw_attachment_thumbnail_512_url
    return entity


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

        if file.content_type not in ["image/png", "image/jpeg"]:
            raise UnsupportedFileType("Profile picture should be png or jpeg")

        if db_entity.profile_picture is None:
            profile_picture = Attachment(
                raw_attachment_url="",
                entity_id=db_entity.id,
                entity_type=self.entity_type,
                attachment_type=AttachmentAttachmentType.PROFILE_PICTURE,
            )
            self.crud.session.add(profile_picture)
        else:
            profile_picture = db_entity.profile_picture

        await self.crud.session.flush()

        filename = f"{db_entity.id}_{self.entity_type.value}_{profile_picture.id}_profile_picture_{timestamp}"

        au = await upload_attachment(file, filename, make_thumbnail=True)

        profile_picture = assign_attachment_urls(profile_picture, au)

        await self.crud.session.commit()
        await self.logger.after_update(
            db_entity, {"profile_picture": "created"}, request=request
        )

    async def delete(self, db_entity: T, request: Request) -> None:
        if db_entity.profile_picture is None:
            return

        await self.crud.session.delete(db_entity.profile_picture)
        await self.crud.session.commit()
        await self.logger.after_update(
            db_entity, {"profile_picture": "created"}, request=request
        )


V = TypeVar("V", bound=AttachmentMixin)


class AttachmentHandler(BaseManager, Generic[V]):
    def __init__(
        self,
        session: AsyncSession,
        current_user: User | None,
        entity_type: AttachmentEntityType,
    ):
        super().__init__(session, current_user)
        self.entity_type = entity_type

    async def set(
        self, files: list[UploadFile], db_entity: V, request: Request
    ) -> None:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")

        for file in files:
            if file.content_type == "application/pdf":
                attachment_type = AttachmentAttachmentType.PDF
            elif file.content_type in ("image/jpeg", "image/png"):
                attachment_type = AttachmentAttachmentType.PICTURE
            else:
                raise UnsupportedFileType("Attachment should be png, jpeg or pdf")

            attachment = Attachment(
                raw_attachment_url="",
                entity_id=db_entity.id,
                entity_type=self.entity_type,
                attachment_type=attachment_type,
            )
            self.crud.session.add(attachment)
            await self.crud.session.flush()

            filename = f"{db_entity.id}_{self.entity_type.value}_{attachment.id}_attachment_{timestamp}"

            au = await upload_attachment(
                file,
                filename,
                make_thumbnail=(attachment_type == AttachmentAttachmentType.PICTURE),
            )

            attachment = assign_attachment_urls(attachment, au)

            await self.crud.session.commit()
            await self.logger.after_update(
                db_entity, {"attachment": "created"}, request=request
            )

    async def delete(self, db_entity: V, attachment_id: int, request: Request) -> None:
        was_deleted = False
        for attachment in db_entity.attachments:
            if attachment.id == attachment_id:
                await self.crud.session.delete(attachment)
                was_deleted = True

        if not was_deleted:
            raise EntityNotFound("Attachment not found")

        await self.crud.session.commit()
        await self.logger.after_update(
            db_entity, {"attachment": "created"}, request=request
        )
