from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    from . import requests_compat as requests

KOREAN_KEYWORDS = [
    "모닝브리핑",
    "장전 시황",
    "오늘 시황",
    "미국증시",
    "증시 브리핑",
    "뉴욕증시",
    "시장 브리핑",
]


class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: str, session: requests.Session | None = None):
        self.api_key = api_key
        self.session = session or requests.Session()

    @staticmethod
    def seoul_date_window(date_str: str) -> tuple[str, str]:
        seoul = ZoneInfo("Asia/Seoul")
        start = datetime.fromisoformat(date_str).replace(tzinfo=seoul)
        end = start + timedelta(days=1)
        return start.isoformat(), end.isoformat()

    def search_morning_briefs(self, date_str: str, limit: int = 20) -> list[dict]:
        published_after, published_before = self.seoul_date_window(date_str)
        query = " OR ".join(KOREAN_KEYWORDS)
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(limit, 50),
            "order": "relevance",
            "videoCaption": "closedCaption",
            "publishedAfter": published_after,
            "publishedBefore": published_before,
            "key": self.api_key,
            "regionCode": "KR",
            "relevanceLanguage": "ko",
        }
        resp = self._request_with_retries(self.BASE_URL, params=params)
        items = resp.json().get("items", [])
        results = []
        now = datetime.utcnow().isoformat()
        for item in items[:limit]:
            vid = item["id"]["videoId"]
            snippet = item["snippet"]
            results.append(
                {
                    "video_id": vid,
                    "date": date_str,
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "fetched_at": now,
                }
            )
        return results

    def _request_with_retries(self, url: str, params: dict, max_retries: int = 3) -> requests.Response:
        for attempt in range(max_retries):
            r = self.session.get(url, params=params, timeout=30)
            if r.status_code < 400:
                return r
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep((2**attempt) + random.uniform(0.5, 1.5))
                continue
            r.raise_for_status()
        r.raise_for_status()
        return r
