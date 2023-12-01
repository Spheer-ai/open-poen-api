from pydantic import BaseModel


class ProfilePicture(BaseModel):
    id: int
    attachment_url: str
    attachment_thumbnail_url_128: str
    attachment_thumbnail_url_256: str
    attachment_thumbnail_url_512: str

    class Config:
        orm_mode = True


class Attachment(BaseModel):
    id: int
    attachment_url: str
    attachment_thumbnail_url_128: str | None
    attachment_thumbnail_url_256: str | None
    attachment_thumbnail_url_512: str | None

    class Config:
        orm_mode = True
