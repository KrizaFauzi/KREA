"""TikTok research data via RapidAPI.

Part 1 of KREA (product research) needs real signal about what is trending on
TikTok in a niche. This module does a single keyword search against a RapidAPI
TikTok scraper and returns a *simplified*, model-friendly list of videos.

It's intentionally defensive: RapidAPI TikTok providers differ in JSON shape, so
parsing digs through a few common layouts and never raises — on any problem it
returns {"error": "..."} so the agent can recover (e.g. fall back to plain
brainstorming and tell the user to set RAPIDAPI_KEY).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.config import settings

_TIMEOUT = 20  # seconds

# RapidAPI sits behind Cloudflare, which 403s the default urllib User-Agent
# ("error code: 1010"). Send a normal browser UA so requests get through.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among keys."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) is not None:
            return d[k]
    return default


def _extract_videos(payload: Any) -> list[dict]:
    """Find the list of video objects inside a variety of provider shapes."""
    if isinstance(payload, list):
        return [v for v in payload if isinstance(v, dict)]
    if not isinstance(payload, dict):
        return []
    # Common nests: {data:{videos:[...]}}, {data:[...]}, {videos:[...]}, {aweme_list:[...]}
    data = payload.get("data", payload)
    for container in (data, payload):
        if isinstance(container, dict):
            for key in ("videos", "aweme_list", "item_list", "list", "items"):
                v = container.get(key)
                if isinstance(v, list):
                    return [x for x in v if isinstance(x, dict)]
        if isinstance(container, list):
            return [x for x in container if isinstance(x, dict)]
    return []


def _simplify(v: dict) -> dict:
    """Pull the fields useful for product/trend research from one video object."""
    author = v.get("author")
    if isinstance(author, dict):
        author_name = _first(author, "nickname", "unique_id", "uniqueId", "nick_name", default="")
    else:
        author_name = author or ""

    stats = v.get("stats") if isinstance(v.get("stats"), dict) else v
    return {
        "title": _first(v, "title", "desc", "description", default="")[:300],
        "author": author_name,
        "plays": _first(stats, "play_count", "playCount", "play", default=0),
        "likes": _first(stats, "digg_count", "diggCount", "likes", "like_count", default=0),
        "comments": _first(stats, "comment_count", "commentCount", "comments", default=0),
        "shares": _first(stats, "share_count", "shareCount", "shares", default=0),
    }


def search(keywords: str, count: int = 15) -> dict[str, Any]:
    """Search TikTok for `keywords` and return simplified trending videos.

    Returns {"keywords", "count", "items": [...]} on success, or {"error": ...}.
    """
    if not settings.rapidapi_key:
        return {
            "error": "RAPIDAPI_KEY belum diset di .env, jadi data TikTok real-time "
            "tidak tersedia. Isi key-nya dulu, atau lanjut brainstorming dari "
            "pengetahuan umum."
        }

    count = max(1, min(int(count or 15), 30))
    query = {
        settings.tiktok_query_param: keywords,
        "count": count,
        "region": settings.tiktok_region,
        # tiktok-api23 paginates by these; harmless extras for other providers.
        "cursor": "0",
        "search_id": "0",
    }
    url = (
        f"https://{settings.rapidapi_host}{settings.tiktok_search_path}"
        f"?{urllib.parse.urlencode(query)}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "x-rapidapi-key": settings.rapidapi_key,
            "x-rapidapi-host": settings.rapidapi_host,
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return {"error": f"TikTok API HTTP {exc.code}: {exc.reason}. Cek RAPIDAPI_HOST/PATH & langganan API-mu."}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"error": f"Gagal menghubungi TikTok API: {exc}"}
    except json.JSONDecodeError:
        return {"error": "Respons TikTok API bukan JSON yang valid."}

    videos = _extract_videos(payload)
    if not videos:
        return {
            "keywords": keywords,
            "count": 0,
            "items": [],
            "note": "API merespons tapi tidak ada video yang bisa diparse. Mungkin "
            "format provider berbeda — sesuaikan parsing di backend/tiktok.py.",
        }

    items = [_simplify(v) for v in videos[:count]]
    return {"keywords": keywords, "count": len(items), "items": items}
