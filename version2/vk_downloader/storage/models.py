from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(BigInteger, nullable=False)
    owner_id = Column(BigInteger, nullable=False)
    title = Column(String, default="")
    url = Column(String, nullable=False)
    media_type = Column(String(10), nullable=False)  # photo/video/doc
    size_bytes = Column(BigInteger, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    download_path = Column(String, default=None)
    downloaded_at = Column(DateTime, default=None)
    is_private = Column(Boolean, default=False)
    date = Column(BigInteger, default=0)  # timestamp VK

    tags = relationship("Tag", back_populates="media_item", cascade="all, delete-orphan")
    meta = relationship("MediaMetadata", back_populates="media_item", cascade="all, delete-orphan")

class Filter(Base):
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    params = Column(JSON, nullable=False)  # dict с параметрами поиска
    created_at = Column(DateTime, default=datetime.utcnow)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    tag_name = Column(String, nullable=False)

    media_item = relationship("MediaItem", back_populates="tags")

class MediaMetadata(Base):
    __tablename__ = "metadata"

    id = Column(Integer, primary_key=True)
    media_id = Column(Integer, ForeignKey("media_items.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, default="")

    media_item = relationship("MediaItem", back_populates="meta")