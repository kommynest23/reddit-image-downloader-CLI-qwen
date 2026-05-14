"""Database models for storing media items."""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MediaItem(Base):
    """Model for media items."""
    __tablename__ = 'media_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(String(50), unique=True, nullable=False)
    owner_id = Column(Integer, nullable=False)
    title = Column(String(500))
    description = Column(Text)
    url = Column(String(1000), nullable=False)
    media_type = Column(String(20), nullable=False)  # photo, video, doc
    size_bytes = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime)
    download_path = Column(String(1000))
    downloaded_at = Column(DateTime)
    is_private = Column(Boolean, default=False)
    album_id = Column(String(50))


class Filter(Base):
    """Model for saved filters."""
    __tablename__ = 'filters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    params = Column(Text)  # JSON string of filter parameters
    created_at = Column(DateTime)


class Tag(Base):
    """Model for tags associated with media items."""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, nullable=False)  # FK to media_items.id
    tag_name = Column(String(50), nullable=False)
    created_at = Column(DateTime)


class Metadata(Base):
    """Model for additional metadata for media items."""
    __tablename__ = 'metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, nullable=False)  # FK to media_items.id
    key = Column(String(100), nullable=False)
    value = Column(Text)