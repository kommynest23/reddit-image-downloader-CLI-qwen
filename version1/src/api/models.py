"""Pydantic models for VK API responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VKPhotoSize(BaseModel):
    """Model for photo size information."""
    type: str = Field(..., description="Size type (s, m, x, o, p, q, r, y, z, w)")
    url: str = Field(..., description="URL to the image")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")


class VKPhoto(BaseModel):
    """Model for VK photo object."""
    id: int = Field(..., description="Photo ID")
    album_id: int = Field(..., description="Album ID")
    owner_id: int = Field(..., description="Owner ID")
    photo_75: Optional[str] = Field(None, description="URL to the smallest photo")
    photo_130: Optional[str] = Field(None, description="URL to medium-sized photo")
    photo_604: Optional[str] = Field(None, description="URL to large photo")
    photo_807: Optional[str] = Field(None, description="URL to extra large photo")
    photo_1280: Optional[str] = Field(None, description="URL to extra extra large photo")
    photo_2560: Optional[str] = Field(None, description="URL to the largest photo")
    width: Optional[int] = Field(None, description="Original photo width")
    height: Optional[int] = Field(None, description="Original photo height")
    text: str = Field("", description="Text description of the photo")
    date: int = Field(..., description="Date when the photo was added")
    sizes: List[VKPhotoSize] = Field(default_factory=list, description="Available photo sizes")
    
    def get_largest_photo_url(self) -> Optional[str]:
        """Get the URL of the largest available photo."""
        if not self.sizes:
            # Fallback to named fields if sizes array is empty
            for attr in ['photo_2560', 'photo_1280', 'photo_807', 'photo_604', 'photo_130', 'photo_75']:
                url = getattr(self, attr, None)
                if url:
                    return url
            return None
        
        # Find the size with the largest area
        largest_size = max(self.sizes, key=lambda s: s.width * s.height)
        return largest_size.url


class VKVideo(BaseModel):
    """Model for VK video object."""
    id: int = Field(..., description="Video ID")
    owner_id: int = Field(..., description="Owner ID")
    title: str = Field(..., description="Video title")
    description: str = Field("", description="Video description")
    duration: int = Field(..., description="Duration in seconds")
    photo_130: Optional[str] = Field(None, description="URL to small preview photo")
    photo_320: Optional[str] = Field(None, description="URL to medium preview photo")
    photo_640: Optional[str] = Field(None, description="URL to large preview photo")
    photo_800: Optional[str] = Field(None, description="URL to extra large preview photo")
    date: int = Field(..., description="Upload date")
    views: int = Field(..., description="Number of views")
    comments: int = Field(..., description="Number of comments")
    
    def get_best_preview_url(self) -> Optional[str]:
        """Get the best available preview URL."""
        for attr in ['photo_800', 'photo_640', 'photo_320', 'photo_130']:
            url = getattr(self, attr, None)
            if url:
                return url
        return None


class VKDoc(BaseModel):
    """Model for VK document object."""
    id: int = Field(..., description="Document ID")
    owner_id: int = Field(..., description="Owner ID")
    title: str = Field(..., description="Document title")
    size: int = Field(..., description="File size in bytes")
    ext: str = Field(..., description="File extension")
    url: str = Field(..., description="Direct URL to the document")
    date: int = Field(..., description="Upload date")
    type: int = Field(..., description="Document type (1=image, 2=audio_message, etc.)")
    preview: Optional[Dict[str, Any]] = Field(None, description="Preview information")


class VKMediaAttachment(BaseModel):
    """Model for media attachment in a post."""
    type: str = Field(..., description="Type of attachment (photo, video, doc, etc.)")
    photo: Optional[VKPhoto] = Field(None, description="Photo attachment")
    video: Optional[VKVideo] = Field(None, description="Video attachment")
    doc: Optional[VKDoc] = Field(None, description="Document attachment")


class VKWallPost(BaseModel):
    """Model for VK wall post."""
    id: int = Field(..., description="Post ID")
    owner_id: int = Field(..., description="Owner ID")
    from_id: int = Field(..., description="ID of the poster")
    date: int = Field(..., description="Post date")
    post_type: str = Field(..., description="Type of post")
    text: str = Field("", description="Post text")
    attachments: List[VKMediaAttachment] = Field(default_factory=list, description="Attached media")
    likes: Optional[Dict[str, int]] = Field(None, description="Likes count")
    reposts: Optional[Dict[str, int]] = Field(None, description="Reposts count")
    views: Optional[Dict[str, int]] = Field(None, description="Views count")


class VKApiResponse(BaseModel):
    """Generic model for VK API responses."""
    response: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, int]] = Field(None, description="Error information if any")
    
    class Config:
        extra = "allow"
"""Pydantic models for Reddit API responses."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from urllib.parse import urlparse


class MediaInfo(BaseModel):
    """Information about media in a Reddit post."""
    url: str = Field(..., description="Direct URL to the media")
    width: Optional[int] = Field(None, description="Width of the media in pixels")
    height: Optional[int] = Field(None, description="Height of the media in pixels")
    is_video: bool = Field(False, description="Whether the media is a video")


class RedditPost(BaseModel):
    """Model for a Reddit post with media content."""
    id: str = Field(..., description="Reddit post ID")
    title: str = Field(..., description="Title of the post")
    author: str = Field(..., description="Author of the post")
    score: int = Field(..., description="Score/votes of the post")
    created_utc: float = Field(..., description="Creation timestamp in UTC")
    subreddit: str = Field(..., description="Subreddit name")
    url: str = Field(..., description="URL to the Reddit post")
    permalink: str = Field(..., description="Permalink to the post")
    is_video: bool = Field(False, description="Whether the post contains video")
    nsfw: bool = Field(False, description="Whether the post is marked as NSFW")
    media: Optional[MediaInfo] = Field(None, description="Media information")
    num_comments: int = Field(0, description="Number of comments on the post")
    thumbnail: Optional[str] = Field(None, description="Thumbnail URL")
    preview_images: List[str] = Field(default_factory=list, description="Preview image URLs")
    
    def extract_image_url(self) -> Optional[str]:
        """
        Extract the direct URL to the image/video from the post.
        
        Returns:
            Direct URL to the media content or None if not available
        """
        if self.media and self.media.url:
            return self.media.url
            
        # Check for preview images
        if self.preview_images:
            return self.preview_images[0]
            
        # Check if URL itself is a direct image link
        parsed = urlparse(self.url)
        if parsed.netloc in ['i.redd.it', 'i.imgur.com', 'imgur.com']:
            if any(parsed.path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.mp4']):
                return self.url
                
        return None


class RedditUser(BaseModel):
    """Model for Reddit user information."""
    name: str = Field(..., description="Username")
    created_utc: float = Field(..., description="Account creation timestamp in UTC")
    comment_karma: int = Field(..., description="Comment karma")
    link_karma: int = Field(..., description="Link karma")


class APIResponse(BaseModel):
    """Generic model for Reddit API responses."""
    kind: str = Field(..., description="Type of object returned (Listing, t3, etc.)")
    data: Dict[str, Any] = Field(..., description="Response data")
    
    class Config:
        extra = "allow"