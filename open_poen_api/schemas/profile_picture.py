from pydantic import BaseModel


class ProfilePicture(BaseModel):
    id: int
    attachment_url: str
    attachment_thumbnail_url_128: str
    attachment_thumbnail_url_256: str
    attachment_thumbnail_url_512: str

    class Config:
        orm_mode = True
