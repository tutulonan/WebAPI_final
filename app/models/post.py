from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class RSSPost(Base):
    __tablename__ = "rss_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), index=True)
    link = Column(String(500), unique=True, index=True)  # уникальный URL
    summary = Column(Text)
    published = Column(String(50))   # ISO 8601 или как в RSS
    author = Column(String(100))
    category = Column(String(100))   # hub / tag
    source = Column(String(50), default="habr")  # "habr", "manual", "external"
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())