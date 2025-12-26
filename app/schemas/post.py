from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class RSSPostBase(BaseModel):
    title: str
    link: str
    summary: Optional[str] = None
    published: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    source: str = "habr"

    model_config = ConfigDict(from_attributes=True)


class RSSPostCreate(RSSPostBase):
    pass


class RSSPostUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None


class RSSPostResponse(RSSPostBase):
    id: int
    created_at: datetime
    updated_at: datetime

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        for field in ['created_at', 'updated_at']:
            if field in data and isinstance(data[field], datetime):
                data[field] = data[field].isoformat()
        return data


class RSSUpdateEvent(BaseModel):
    type: str = "rss_post_created"
    post_id: int
    title: str
    link: str
    source: str
    timestamp: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)