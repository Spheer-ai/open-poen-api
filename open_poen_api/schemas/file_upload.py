from pydantic import BaseModel
from enum import Enum


class FileUploadType(str, Enum):
    PROFILE_PICTURE = "profile_picture"
    PICTURE = "picture"
    DOCUMENT = "document"
