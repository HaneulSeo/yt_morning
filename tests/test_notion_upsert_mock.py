from __future__ import annotations

from typing import Any

from ytbrief.notion_client import NotionClient


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        raise RuntimeError(self._payload)


class FakeSession:
    def __init__(self):
        self.calls = []

    def request(self, method, url, headers=None, json=None, timeout=45):
        self.calls.append((method, url, json))
        if url.endswith("/query"):
            return FakeResponse(200, {"results": [{"id": "page1"}]})
        if "/blocks/page1/children" in url and method == "GET":
            return FakeResponse(200, {"results": [{"id": "block1"}]})
        return FakeResponse(200, {"id": "page1"})


def test_notion_upsert_updates_existing_page():
    session = FakeSession()
    client = NotionClient("token", "db1", session=session)
    digest = {
        "one_liner": "요약",
        "consensus": ["a", "b", "c"],
        "differences": ["d1", "d2", "d3"],
        "checklist": ["c1", "c2", "c3"],
        "top_topics": ["반도체"],
        "sources": [{"title": "t", "url": "u", "channel": "ch"}],
    }
    page_id = client.upsert_daily_page("2026-02-19", digest, video_count=3)
    assert page_id == "page1"
    methods = [c[0] for c in session.calls]
    assert "DELETE" in methods
    assert "PATCH" in methods
