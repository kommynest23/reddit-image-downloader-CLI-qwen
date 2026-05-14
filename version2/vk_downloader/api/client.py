import time
import asyncio
import httpx
from typing import Optional, Dict, Any, Type, TypeVar, List
from loguru import logger
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class VKAPIError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"VK API Error [{code}]: {message}")

class VKAPIClient:
    BASE_URL = "https://api.vk.com/method/"
    _rate_lock = asyncio.Lock()
    _last_call = 0.0
    MIN_INTERVAL = 1.0 / 3  # 3 запроса в секунду

    def __init__(self, token: str, api_version: str = "5.199"):
        self.token = token
        self.api_version = api_version
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self.client.aclose()

    async def _rate_limit(self):
        async with self._rate_lock:
            now = time.monotonic()
            wait = self.MIN_INTERVAL - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()

    async def _request(self, method: str, params: Dict[str, Any], model: Type[T] = None) -> Optional[Any]:
        await self._rate_limit()
        params["access_token"] = self.token
        params["v"] = self.api_version
        url = f"{self.BASE_URL}{method}"
        logger.debug(f"API call: {method} with {params}")
        try:
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise SystemExit(2)

        if "error" in data:
            error = data["error"]
            code = error.get("error_code")
            msg = error.get("error_msg", "")
            logger.error(f"VK error {code}: {msg}")
            if code in (6, 9):  # Too many requests / Flood control
                logger.warning("Rate limit hit, retrying after 1 sec...")
                await asyncio.sleep(1)
                return await self._request(method, params, model)
            raise VKAPIError(code, msg)

        if model and "response" in data:
            try:
                return model(**data["response"])
            except ValidationError as e:
                logger.error(f"Response validation failed: {e}")
                raise
        return data.get("response")

    async def users_get(self, user_ids: str = "1") -> list:
        resp = await self._request("users.get", {"user_ids": user_ids})
        return resp

    async def search_media(self, owner_id: int, media_type: str, limit: int,
                           after_date: Optional[int] = None, before_date: Optional[int] = None) -> List[Dict]:
        if media_type in ("photo", "video"):
            return await self._search_media_wall(owner_id, media_type, limit, after_date, before_date)
        elif media_type == "doc":
            return await self._search_media_docs(owner_id, limit)
        else:
            raise ValueError(f"Unsupported media type: {media_type}")

    async def _search_media_wall(self, owner_id: int, media_type: str, limit: int,
                                  after_date: int = None, before_date: int = None) -> List[Dict]:
        items = []
        count_per_request = min(limit, 100)
        offset = 0
        while len(items) < limit:
            params = {
                "owner_id": owner_id,
                "count": count_per_request,
                "offset": offset,
                "extended": 0,
                "filter": "all",
            }
            resp = await self._request("wall.get", params)
            if not resp or "items" not in resp:
                break
            posts = resp["items"]
            if not posts:
                break

            for post in posts:
                if after_date and post["date"] < after_date:
                    continue
                if before_date and post["date"] > before_date:
                    continue
                if "attachments" in post:
                    for att in post["attachments"]:
                        if att["type"] == media_type:
                            media = att[media_type]
                            if media_type == "photo":
                                sizes = media.get("sizes", [])
                                url = ""
                                width = 0
                                height = 0
                                # Сортируем по площади (ширина * высота) по убыванию
                                sorted_sizes = sorted(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0), reverse=True)
                                # Ищем первый размер с непустым URL
                                for s in sorted_sizes:
                                    if s.get("url"):
                                        url = s["url"]
                                        width = s.get("width", 0)
                                        height = s.get("height", 0)
                                        break
                                # Если не нашли, берём любой первый с URL
                                if not url:
                                    for s in sizes:
                                        if s.get("url"):
                                            url = s["url"]
                                            width = s.get("width", 0)
                                            height = s.get("height", 0)
                                            break
                                title = post.get("text", "")[:100]
                                data = {
                                    "id": media["id"],
                                    "owner_id": media["owner_id"],
                                    "title": title,
                                    "url": url,
                                    "media_type": "photo",
                                    "width": width,
                                    "height": height,
                                    "size_bytes": 0,
                                    "date": post["date"],
                                }
                            elif media_type == "video":
                                title = media.get("title", "")
                                url = media.get("player", "")
                                files = media.get("files", {})
                                if files:
                                    # Ищем ключ с максимальным числовым качеством (например "720")
                                    best_quality = max(files.keys(), key=lambda k: int(k) if k.isdigit() else 0)
                                    url = files[best_quality]
                                data = {
                                    "id": media["id"],
                                    "owner_id": media["owner_id"],
                                    "title": title,
                                    "url": url,
                                    "media_type": "video",
                                    "width": media.get("width", 0),
                                    "height": media.get("height", 0),
                                    "size_bytes": media.get("size", 0),
                                    "date": post["date"],
                                }
                            items.append(data)
                            if len(items) >= limit:
                                break
                    if len(items) >= limit:
                        break
            if len(posts) < count_per_request:
                break
            offset += count_per_request
        return items

    async def _search_media_docs(self, owner_id: int, limit: int) -> List[Dict]:
        logger.warning("Метод docs.get может быть недоступен с сервисным ключом")
        params = {
            "owner_id": owner_id,
            "count": limit,
        }
        resp = await self._request("docs.get", params)
        if not resp or "items" not in resp:
            return []
        items = []
        for doc in resp["items"]:
            data = {
                "id": doc["id"],
                "owner_id": doc["owner_id"],
                "title": doc["title"],
                "url": doc["url"],
                "media_type": "doc",
                "size_bytes": doc["size"],
                "width": 0,
                "height": 0,
                "date": doc.get("date", 0),
            }
            items.append(data)
        return items[:limit]