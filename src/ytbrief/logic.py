from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress

from .gemini_client import GeminiClient
from .notion_client import NotionClient
from .storage import Storage
from .youtube_client import YouTubeClient


console = Console()


@dataclass
class PipelineResult:
    found: int = 0
    summarized_success: int = 0
    summarized_failed: int = 0
    digest_status: str = "pending"
    notion_page_id: str | None = None


def _sleep_jitter() -> None:
    time.sleep(random.uniform(0.5, 1.5))


def fetch_videos(db: str, date: str, limit: int) -> int:
    yt = YouTubeClient(api_key=os.environ["YOUTUBE_API_KEY"])
    store = Storage(db)
    videos = yt.search_morning_briefs(date, limit=limit)
    for v in videos:
        store.upsert_video(v)
        _sleep_jitter()
    store.close()
    return len(videos)


def summarize_videos(db: str, date: str, model: str) -> tuple[int, int]:
    gemini = GeminiClient(api_key=os.environ["GEMINI_API_KEY"], model=model)
    store = Storage(db)
    videos = store.list_videos_by_date(date)
    ok, failed = 0, 0
    with Progress(console=console) as progress:
        task = progress.add_task("Summarizing videos...", total=len(videos))
        for row in videos:
            try:
                summary = gemini.summarize_video(row["url"])
                store.upsert_video_summary(row["video_id"], date, summary.model_dump_json(ensure_ascii=False), "success")
                ok += 1
            except Exception as exc:  # continue pipeline
                store.upsert_video_summary(row["video_id"], date, json.dumps({"error": str(exc)}, ensure_ascii=False), "failed")
                failed += 1
            progress.advance(task)
            _sleep_jitter()
    store.close()
    return ok, failed


def create_digest(db: str, date: str, model: str) -> str:
    gemini = GeminiClient(api_key=os.environ["GEMINI_API_KEY"], model=model)
    store = Storage(db)
    rows = store.list_successful_summaries(date)
    if not rows:
        store.upsert_daily_digest(date, json.dumps({"error": "no successful summaries"}), "failed")
        store.close()
        return "failed"

    per_video = []
    for r in rows:
        body = json.loads(r["summary_json"])
        body["source"] = {"title": r["title"], "url": r["url"], "channel": r["channel"]}
        per_video.append(body)

    digest = gemini.build_daily_digest(date, per_video).model_dump()
    if not digest.get("sources"):
        digest["sources"] = [{"title": r["title"], "url": r["url"], "channel": r["channel"]} for r in rows]
    store.upsert_daily_digest(date, json.dumps(digest, ensure_ascii=False), "success")
    store.close()
    return "success"


def publish_notion(db: str, date: str) -> str:
    store = Storage(db)
    digest_row = store.get_daily_digest(date)
    if not digest_row or digest_row["status"] != "success":
        store.close()
        raise RuntimeError("No successful daily digest to publish")
    digest = json.loads(digest_row["digest_json"])
    video_count = len(store.list_successful_summaries(date))
    notion = NotionClient(
        token=os.environ["NOTION_TOKEN"],
        database_id=os.environ["NOTION_DATABASE_ID"],
        notion_version=os.getenv("NOTION_VERSION", "2022-06-28"),
    )
    page_id = notion.upsert_daily_page(date, digest, video_count)
    store.set_notion_page_id(date, page_id)
    store.close()
    return page_id


def run_pipeline(db: str, date: str, limit: int, model: str) -> PipelineResult:
    result = PipelineResult()
    result.found = fetch_videos(db, date, limit)
    result.summarized_success, result.summarized_failed = summarize_videos(db, date, model)
    result.digest_status = create_digest(db, date, model)
    if result.digest_status == "success":
        result.notion_page_id = publish_notion(db, date)
    return result
