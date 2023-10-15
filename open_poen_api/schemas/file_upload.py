from pydantic import BaseModel
from enum import Enum


class FileUploadEntityClass(str, Enum):
    USER = "User"


class FileUploadType(str, Enum):
    PROFILE_PICTURE = "profile_picture"
    PICTURE = "picture"
    DOCUMENT = "document"


class FileUploadCreate(BaseModel):
    entity_class: FileUploadEntityClass
    entity_id: int
    upload_type: FileUploadType
