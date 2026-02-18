from __future__ import annotations

import random
import time
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    from . import requests_compat as requests


class NotionClient:
    BASE_URL = "https://api.notion.com/v1"

    def __init__(self, token: str, database_id: str, notion_version: str = "2022-06-28", session: requests.Session | None = None):
        self.database_id = database_id
        self.session = session or requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
            "Content-Type": "application/json",
        }

    def upsert_daily_page(self, date: str, digest: dict, video_count: int) -> str:
        page = self.find_page_by_date(date)
        properties = self._build_properties(date, digest, video_count)
        children = self._build_children(digest)
        if page:
            page_id = page["id"]
            self._request_with_retries("PATCH", f"/pages/{page_id}", json={"properties": properties})
            self._replace_children(page_id, children)
            return page_id
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": children,
        }
        created = self._request_with_retries("POST", "/pages", json=payload).json()
        return created["id"]

    def find_page_by_date(self, date: str) -> dict[str, Any] | None:
        payload = {
            "filter": {"property": "Date", "date": {"equals": date}},
            "page_size": 1,
        }
        resp = self._request_with_retries("POST", f"/databases/{self.database_id}/query", json=payload)
        results = resp.json().get("results", [])
        return results[0] if results else None

    def _replace_children(self, page_id: str, new_children: list[dict]) -> None:
        existing = self._list_children(page_id)
        for block in existing:
            self._request_with_retries("DELETE", f"/blocks/{block['id']}")
            time.sleep(random.uniform(0.5, 1.1))
        self._request_with_retries("PATCH", f"/blocks/{page_id}/children", json={"children": new_children})

    def _list_children(self, page_id: str) -> list[dict]:
        url = f"/blocks/{page_id}/children?page_size=100"
        data = self._request_with_retries("GET", url).json()
        return data.get("results", [])

    def _build_properties(self, date: str, digest: dict, video_count: int) -> dict:
        summary_text = digest["one_liner"] + "\n" + "\n".join(f"- {x}" for x in digest["consensus"])
        confidence = "medium"
        return {
            "Name": {"title": [{"text": {"content": f"{date} Morning Brief"}}]},
            "Date": {"date": {"start": date}},
            "VideoCount": {"number": video_count},
            "Summary": {"rich_text": [{"text": {"content": summary_text[:1900]}}]},
            "Topics": {"multi_select": [{"name": t[:100]} for t in digest.get("top_topics", [])[:20]]},
            "Confidence": {"select": {"name": confidence}},
        }

    def _build_children(self, digest: dict) -> list[dict]:
        def heading(txt: str) -> dict:
            return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [{"type": "text", "text": {"content": txt}}]}}

        def para(txt: str) -> dict:
            return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": txt[:1900]}}]}}

        def bullets(items: list[str]) -> list[dict]:
            return [
                {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": i[:1900]}}]}}
                for i in items
            ]

        sources = [f"{s['title']} | {s['url']} | {s['channel']}" for s in digest.get("sources", [])]
        blocks = [heading("오늘 한줄"), para(digest["one_liner"]), heading("컨센서스")]
        blocks.extend(bullets(digest.get("consensus", [])))
        blocks.append(heading("관점 차이"))
        blocks.extend(bullets(digest.get("differences", [])))
        blocks.append(heading("체크리스트"))
        blocks.extend(bullets(digest.get("checklist", [])))
        blocks.append(heading("Sources"))
        blocks.extend(bullets(sources))
        return blocks

    def _request_with_retries(self, method: str, path: str, json: dict | None = None, max_retries: int = 4) -> requests.Response:
        for attempt in range(max_retries):
            resp = self.session.request(
                method,
                f"{self.BASE_URL}{path}",
                headers=self.headers,
                json=json,
                timeout=45,
            )
            if resp.status_code < 400:
                return resp
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep((2**attempt) + random.uniform(0.5, 1.5))
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return resp
