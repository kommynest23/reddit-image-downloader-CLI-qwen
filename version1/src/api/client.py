"""Asynchronous VK API client with rate limiting and caching."""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx
from src.api.models import VKApiResponse, VKPhoto, VKVideo, VKDoc, VKWallPost
from src.config.manager import ConfigManager
from src.utils.logger import logger


class VKAPIError(Exception):
    """Raised when there's an issue with VK API requests."""
    pass


class RateLimitError(VKAPIError):
    """Raised when VK API rate limit is exceeded."""
    pass


class VKAPIClient:
    """Asynchronous client for interacting with VK API."""
    
    BASE_URL = "https://api.vk.com/method/"
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the VK API client.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.config = config_manager.config
        
        # Track rate limits
        self.last_request_time = 0
        self.requests_this_second = 0
        
        # Create cache directory
        if self.config.cache.enabled:
            self.cache_dir = self.config.cache.cache_directory / "api"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def _make_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        method_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to the VK API.
        
        Args:
            method: VK API method to call
            params: Parameters for the API call
            method_options: Additional options for the request
            
        Returns:
            JSON response from the API
        """
        if params is None:
            params = {}
        
        # Add required parameters
        params.update({
            'access_token': self.config.vk.service_token,
            'v': self.config.vk.api_version
        })
        
        # Check for cached response
        cache_key = self._generate_cache_key(method, params)
        cache_file = self.cache_dir / f"{cache_key}.json" if self.config.cache.enabled else None
        
        if self.config.cache.enabled and cache_file and cache_file.exists():
            try:
                cached_data = self._load_from_cache(cache_file)
                if cached_data and not self._is_cache_expired(cached_data):
                    logger.debug(f"Returning cached response for {method}")
                    return cached_data["data"]
            except Exception as e:
                logger.warning(f"Could not load from cache: {e}")
        
        # Enforce rate limiting (max 3 requests per second)
        current_time = time.time()
        if current_time - self.last_request_time < 1:
            if self.requests_this_second >= 3:
                sleep_time = 1 - (current_time - self.last_request_time)
                logger.debug(f"Rate limit approaching, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                # Reset counters after sleep
                self.last_request_time = time.time()
                self.requests_this_second = 0
        else:
            # Reset counter if it's a new second
            self.requests_this_second = 0
            self.last_request_time = current_time
        
        self.requests_this_second += 1
        
        url = f"{self.BASE_URL}{method}"
        
        try:
            async with httpx.AsyncClient(timeout=self.config.download.timeout_seconds) as client:
                response = await client.get(url, params=params)
                
                # Check for VK API errors
                response_json = response.json()
                
                if 'error' in response_json:
                    error = response_json['error']
                    error_code = error.get('error_code', 0)
                    
                    # Handle specific VK API errors
                    if error_code == 6:  # Too many requests per second
                        logger.warning("VK API rate limit exceeded (error 6), waiting 1 second")
                        await asyncio.sleep(1)
                        # Retry the request once
                        response = await client.get(url, params=params)
                        response_json = response.json()
                        
                        if 'error' in response_json:
                            raise VKAPIError(f"VK API error after retry: {response_json['error']}")
                    elif error_code == 9:  # Flood control
                        logger.warning("VK API flood control (error 9), waiting 5 seconds")
                        await asyncio.sleep(5)
                        raise VKAPIError(f"VK API flood control error: {error}")
                    elif error_code == 14:  # Captcha needed
                        raise VKAPIError(f"VK API captcha needed: {error}")
                    elif error_code == 15:  # Access denied
                        raise VKAPIError(f"VK API access denied: {error}")
                    else:
                        raise VKAPIError(f"VK API error: {error}")
                
                # Cache successful response
                if self.config.cache.enabled and cache_file:
                    try:
                        self._save_to_cache(cache_file, response_json)
                    except Exception as e:
                        logger.warning(f"Could not save to cache: {e}")
                
                return response_json
                
        except httpx.RequestError as e:
            logger.error(f"Network error during API request: {e}")
            raise VKAPIError(f"Network error during API request: {e}")
    
    def _generate_cache_key(self, method: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key for the given request."""
        # Sort params to ensure consistent keys
        sorted_params = tuple(sorted(params.items()))
        cache_input = f"{method}_{sorted_params}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]
    
    def _load_from_cache(self, cache_file: Path) -> Optional[Dict[str, Any]]:
        """Load data from cache file if it exists."""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def _is_cache_expired(self, cached_data: Dict[str, Any]) -> bool:
        """Check if cached data is expired based on TTL."""
        if "timestamp" not in cached_data:
            return True
            
        age = time.time() - cached_data["timestamp"]
        ttl_seconds = self.config.cache.ttl_hours * 3600
        return age > ttl_seconds
    
    def _save_to_cache(self, cache_file: Path, data: Dict[str, Any]) -> None:
        """Save data to cache file with timestamp."""
        cache_data = {
            "timestamp": time.time(),
            "data": data
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f)
    
    async def get_user_photos(
        self,
        user_id: str,
        count: int = 30,
        offset: int = 0,
        extended: bool = False
    ) -> List[VKPhoto]:
        """
        Get photos from a user's wall or profile.
        
        Args:
            user_id: VK user ID or screen name
            count: Number of photos to return (max 200)
            offset: Offset for pagination
            extended: Whether to return extended info
            
        Returns:
            List of VKPhoto objects
        """
        if count > 200:
            logger.warning("VK API limits requests to 200 photos. Limiting to 200.")
            count = 200
            
        params = {
            "owner_id": user_id,
            "extended": 1 if extended else 0,
            "count": count,
            "offset": offset,
            "album_id": "wall",  # Get photos from wall
            "photo_sizes": 1     # Return all available sizes
        }
        
        response_data = await self._make_request("photos.get", params)
        
        photos = []
        if "response" in response_data and "items" in response_data["response"]:
            for item in response_data["response"]["items"]:
                try:
                    photo = VKPhoto(**item)
                    photos.append(photo)
                except Exception as e:
                    logger.warning(f"Could not process photo data: {e}")
                    continue
        
        return photos
    
    async def get_wall_posts(
        self,
        owner_id: str,
        count: int = 30,
        offset: int = 0
    ) -> List[VKWallPost]:
        """
        Get wall posts from a user or group.
        
        Args:
            owner_id: VK user or group ID
            count: Number of posts to return (max 100)
            offset: Offset for pagination
            
        Returns:
            List of VKWallPost objects
        """
        if count > 100:
            logger.warning("VK API limits requests to 100 posts. Limiting to 100.")
            count = 100
            
        params = {
            "owner_id": owner_id,
            "count": count,
            "offset": offset,
            "extended": 0,
            "fields": ""
        }
        
        response_data = await self._make_request("wall.get", params)
        
        posts = []
        if "response" in response_data and "items" in response_data["response"]:
            for item in response_data["response"]["items"]:
                try:
                    post = VKWallPost(**item)
                    posts.append(post)
                except Exception as e:
                    logger.warning(f"Could not process post data: {e}")
                    continue
        
        return posts
    
    async def search_photos(
        self,
        query: str,
        count: int = 30,
        offset: int = 0
    ) -> List[VKPhoto]:
        """
        Search for public photos.
        
        Args:
            query: Search query
            count: Number of photos to return (max 200)
            offset: Offset for pagination
            
        Returns:
            List of VKPhoto objects
        """
        if count > 200:
            logger.warning("VK API limits requests to 200 photos. Limiting to 200.")
            count = 200
            
        params = {
            "q": query,
            "count": count,
            "offset": offset,
            "photo_sizes": 1     # Return all available sizes
        }
        
        response_data = await self._make_request("photos.search", params)
        
        photos = []
        if "response" in response_data and "items" in response_data["response"]:
            for item in response_data["response"]["items"]:
                try:
                    photo = VKPhoto(**item)
                    photos.append(photo)
                except Exception as e:
                    logger.warning(f"Could not process photo data: {e}")
                    continue
        
        return photos
    
    async def get_user_info(self, user_ids: List[str], fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get user information.
        
        Args:
            user_ids: List of user IDs or screen names
            fields: List of fields to return
            
        Returns:
            List of user information dictionaries
        """
        params = {
            "user_ids": ",".join(user_ids)
        }
        
        if fields:
            params["fields"] = ",".join(fields)
        
        response_data = await self._make_request("users.get", params)
        
        if "response" in response_data:
            return response_data["response"]
        
        return []