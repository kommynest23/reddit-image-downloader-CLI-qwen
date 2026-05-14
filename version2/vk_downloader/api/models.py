from pydantic import BaseModel
from typing import List, Optional

class VKPhotoSize(BaseModel):
    url: str
    width: int
    height: int
    type: str

class VKPhoto(BaseModel):
    id: int
    owner_id: int
    date: int
    sizes: List[VKPhotoSize]
    text: str = ""

class VKVideo(BaseModel):
    id: int
    owner_id: int
    title: str
    duration: int
    date: int
    files: Optional[dict] = None  # содержит ссылки на видео разного качества

class VKDoc(BaseModel):
    id: int
    owner_id: int
    title: str
    size: int
    ext: str
    date: int
    url: str

class VKSearchResponse(BaseModel):
    count: int
    items: list