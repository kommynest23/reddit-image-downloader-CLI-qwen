"""Database operations for the VK Media Downloader."""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.exc import IntegrityError

from src.utils.logger import logger

Base = declarative_base()


class MediaItem(Base):
    """Model for media items downloaded from VK."""
    __tablename__ = 'media_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    vk_id = Column(String(50), unique=True, nullable=False, index=True)  # UNIQUE constraint
    owner_id = Column(Integer, nullable=False, index=True)
    title = Column(String(500))
    description = Column(Text)
    url = Column(String(1000), nullable=False)
    media_type = Column(String(20), nullable=False)  # photo, video, doc
    size_bytes = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    download_path = Column(String(1000))
    downloaded_at = Column(DateTime)
    is_private = Column(Boolean, default=False)
    album_id = Column(String(50), index=True)

    # Relationships
    tags = relationship("Tag", back_populates="media_item", cascade="all, delete-orphan")
    metadata_items = relationship("Metadata", back_populates="media_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MediaItem(vk_id='{self.vk_id}', type='{self.media_type}')>"


class Filter(Base):
    """Model for saved search filters."""
    __tablename__ = 'filters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    params = Column(Text)  # JSON string of filter parameters
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Filter(name='{self.name}')>"


class Tag(Base):
    """Model for tags associated with media items."""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey('media_items.id'), nullable=False, index=True)
    tag_name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    media_item = relationship("MediaItem", back_populates="tags")

    __table_args__ = (
        # Unique constraint: no duplicate tags per media item
        {'sqlite_autoincrement': True}
    )

    def __repr__(self):
        return f"<Tag(media_id={self.media_id}, name='{self.tag_name}')>"


class Metadata(Base):
    """Model for additional key-value metadata for media items."""
    __tablename__ = 'metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(Integer, ForeignKey('media_items.id'), nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    media_item = relationship("MediaItem", back_populates="metadata_items")

    __table_args__ = (
        # Unique constraint: one value per key per media item
        {'sqlite_autoincrement': True}
    )

    def __repr__(self):
        return f"<Metadata(media_id={self.media_id}, key='{self.key}')>"


class DatabaseManager:
    """Manages database operations for the VK Media Downloader."""
    
    def __init__(self, db_path: str = "vk_media.db"):
        """Initialize the database manager and create tables if needed."""
        # Ensure parent directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            connect_args={"check_same_thread": False}  # Required for SQLite with threads
        )
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def close(self):
        """Close the database session."""
        self.session.close()
    
    def add_media_item(self, 
                      vk_id: str, 
                      owner_id: int, 
                      title: str, 
                      url: str, 
                      media_type: str,
                      size_bytes: Optional[int] = None,
                      width: Optional[int] = None,
                      height: Optional[int] = None,
                      description: Optional[str] = None,
                      is_private: bool = False,
                      album_id: Optional[str] = None) -> MediaItem:
        """
        Add or update a media item in the database (upsert by vk_id).
        
        Args:
            vk_id: Unique VK identifier (e.g., "photo_-1_123456")
            owner_id: VK owner ID (negative for groups, positive for users)
            title: Media title or post text
            url: Direct URL to the media file
            media_type: Type of media ("photo", "video", "doc")
            size_bytes: File size in bytes (optional)
            width: Image/video width in pixels (optional)
            height: Image/video height in pixels (optional)
            description: Media description (optional)
            is_private: Whether media is private (default: False)
            album_id: VK album ID if applicable (optional)
            
        Returns:
            MediaItem: The created or updated database record
        """
        try:
            # Try to find existing record by unique vk_id
            existing = self.session.query(MediaItem).filter(
                MediaItem.vk_id == vk_id
            ).first()
            
            if existing:
                # UPDATE existing record
                logger.debug(f"Updating existing media: {vk_id}")
                existing.owner_id = owner_id
                existing.title = title
                existing.url = url
                existing.media_type = media_type
                existing.size_bytes = size_bytes
                existing.width = width
                existing.height = height
                existing.description = description
                existing.is_private = is_private
                existing.album_id = album_id
                # Keep original created_at, don't overwrite
                self.session.commit()
                return existing
            else:
                # INSERT new record
                logger.info(f"Adding new media: {vk_id}")
                media_item = MediaItem(
                    vk_id=vk_id,
                    owner_id=owner_id,
                    title=title,
                    description=description,
                    url=url,
                    media_type=media_type,
                    size_bytes=size_bytes,
                    width=width,
                    height=height,
                    created_at=datetime.utcnow(),
                    is_private=is_private,
                    album_id=album_id
                )
                self.session.add(media_item)
                self.session.commit()
                return media_item
                
        except IntegrityError as e:
            # Fallback: if race condition caused duplicate, try to fetch and update
            self.session.rollback()
            logger.warning(f"IntegrityError for {vk_id}, attempting recovery: {e}")
            existing = self.session.query(MediaItem).filter(
                MediaItem.vk_id == vk_id
            ).first()
            if existing:
                # Update with new values
                existing.title = title
                existing.url = url
                existing.media_type = media_type
                self.session.commit()
                return existing
            raise  # Re-raise if we can't recover
    
    def get_media_item_by_vk_id(self, vk_id: str) -> Optional[MediaItem]:
        """Get a media item by its unique VK ID."""
        return self.session.query(MediaItem).filter(
            MediaItem.vk_id == vk_id
        ).first()
    
    def mark_as_downloaded(self, vk_id: str, download_path: str):
        """Mark a media item as downloaded with its local path."""
        media_item = self.get_media_item_by_vk_id(vk_id)
        if media_item:
            media_item.download_path = download_path
            media_item.downloaded_at = datetime.utcnow()
            self.session.commit()
            logger.info(f"Marked {vk_id} as downloaded: {download_path}")
    
    def add_filter(self, name: str, params: Dict[str, Any]) -> Filter:
        """Add or update a saved filter."""
        existing = self.session.query(Filter).filter(Filter.name == name).first()
        if existing:
            import json
            existing.params = json.dumps(params)
            self.session.commit()
            return existing
        
        import json
        filter_item = Filter(
            name=name,
            params=json.dumps(params),
            created_at=datetime.utcnow()
        )
        self.session.add(filter_item)
        self.session.commit()
        return filter_item
    
    def get_filter_by_name(self, name: str) -> Optional[Filter]:
        """Get a saved filter by its name."""
        return self.session.query(Filter).filter(Filter.name == name).first()
    
    def get_all_filters(self) -> List[Filter]:
        """Get all saved filters."""
        return self.session.query(Filter).all()
    
    def delete_filter(self, name: str) -> bool:
        """Delete a filter by name. Returns True if deleted, False if not found."""
        filter_item = self.get_filter_by_name(name)
        if filter_item:
            self.session.delete(filter_item)
            self.session.commit()
            return True
        return False
    
    def add_tag(self, media_id: int, tag_name: str) -> Tag:
        """Add a tag to a media item (ignores duplicates)."""
        # Check if tag already exists for this media
        existing = self.session.query(Tag).filter(
            Tag.media_id == media_id,
            Tag.tag_name == tag_name
        ).first()
        if existing:
            return existing
        
        tag = Tag(
            media_id=media_id,
            tag_name=tag_name,
            created_at=datetime.utcnow()
        )
        self.session.add(tag)
        self.session.commit()
        return tag
    
    def remove_tag(self, media_id: int, tag_name: str) -> bool:
        """Remove a tag from a media item. Returns True if deleted."""
        tag = self.session.query(Tag).filter(
            Tag.media_id == media_id,
            Tag.tag_name == tag_name
        ).first()
        if tag:
            self.session.delete(tag)
            self.session.commit()
            return True
        return False
    
    def get_tags_for_media(self, media_id: int) -> List[str]:
        """Get all tag names for a media item."""
        tags = self.session.query(Tag).filter(Tag.media_id == media_id).all()
        return [t.tag_name for t in tags]
    
    def add_metadata(self, media_id: int, key: str, value: str) -> Metadata:
        """Add or update metadata key-value pair for a media item."""
        existing = self.session.query(Metadata).filter(
            Metadata.media_id == media_id,
            Metadata.key == key
        ).first()
        if existing:
            existing.value = value
            self.session.commit()
            return existing
        
        metadata = Metadata(
            media_id=media_id,
            key=key,
            value=value,
            created_at=datetime.utcnow()
        )
        self.session.add(metadata)
        self.session.commit()
        return metadata
    
    def get_metadata_for_media(self, media_id: int) -> Dict[str, str]:
        """Get all metadata as dict for a media item."""
        items = self.session.query(Metadata).filter(Metadata.media_id == media_id).all()
        return {m.key: m.value for m in items}
    
    def search_media(self, 
                    media_type: Optional[str] = None, 
                    owner_id: Optional[int] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[MediaItem]:
        """
        Search for media items with optional filters.
        
        Args:
            media_type: Filter by media type ("photo", "video", "doc")
            owner_id: Filter by VK owner ID
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of matching MediaItem objects
        """
        query = self.session.query(MediaItem)
        
        if media_type:
            query = query.filter(MediaItem.media_type == media_type)
        
        if owner_id is not None:
            query = query.filter(MediaItem.owner_id == owner_id)
        
        return query.order_by(MediaItem.created_at.desc()).limit(limit).offset(offset).all()
    
    def delete_media_item(self, vk_id: str, remove_files: bool = False) -> bool:
        """
        Delete a media item from the database.
        
        Args:
            vk_id: Unique VK identifier of the item to delete
            remove_files: If True, also delete the local file (caller must handle)
            
        Returns:
            True if deleted, False if not found
        """
        media_item = self.get_media_item_by_vk_id(vk_id)
        if not media_item:
            return False
        
        # Cascade delete will handle tags and metadata
        self.session.delete(media_item)
        self.session.commit()
        logger.info(f"Deleted media item: {vk_id}")
        return True