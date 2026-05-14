import httpx
from typing import Optional

# Резолвит короткое имя (screen_name) в owner_id через API VK
async def resolve_screen_name(access_token: str, screen_name: str) -> Optional[int]:
    url = "https://api.vk.com/method/utils.resolveScreenName"
    params = {
        "screen_name": screen_name,
        "access_token": access_token,
        "v": "5.199"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "response" in data and data["response"]:
            obj = data["response"]
            if obj.get("type") in ("user", "group", "application", "page"):
                # owner_id может быть отрицательным для групп
                if obj["type"] == "group":
                    return -obj["object_id"]
                return obj["object_id"]
    return None