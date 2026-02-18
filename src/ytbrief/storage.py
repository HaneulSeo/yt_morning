from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class Storage:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS videos(
                video_id TEXT PRIMARY KEY,
                date TEXT,
                title TEXT,
                channel TEXT,
                published_at TEXT,
                url TEXT,
                fetched_at TEXT
            );

            CREATE TABLE IF NOT EXISTS video_summaries(
                video_id TEXT,
                date TEXT,
                summary_json TEXT,
                status TEXT,
                created_at TEXT,
                PRIMARY KEY(video_id, date)
            );

            CREATE TABLE IF NOT EXISTS daily_digests(
                date TEXT PRIMARY KEY,
                digest_json TEXT,
                status TEXT,
                created_at TEXT,
                notion_page_id TEXT
            );
            """
        )
        self.conn.commit()

    def upsert_video(self, row: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO videos(video_id, date, title, channel, published_at, url, fetched_at)
            VALUES (:video_id, :date, :title, :channel, :published_at, :url, :fetched_at)
            ON CONFLICT(video_id) DO UPDATE SET
              date=excluded.date,
              title=excluded.title,
              channel=excluded.channel,
              published_at=excluded.published_at,
              url=excluded.url,
              fetched_at=excluded.fetched_at
            """,
            row,
        )
        self.conn.commit()

    def list_videos_by_date(self, date: str) -> list[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM videos WHERE date = ? ORDER BY published_at", (date,))
        return cur.fetchall()

    def upsert_video_summary(self, video_id: str, date: str, summary_json: str, status: str) -> None:
        self.conn.execute(
            """
            INSERT INTO video_summaries(video_id, date, summary_json, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(video_id, date) DO UPDATE SET
              summary_json=excluded.summary_json,
              status=excluded.status,
              created_at=excluded.created_at
            """,
            (video_id, date, summary_json, status, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def list_successful_summaries(self, date: str) -> list[sqlite3.Row]:
        cur = self.conn.execute(
            "SELECT vs.*, v.title, v.url, v.channel FROM video_summaries vs "
            "JOIN videos v ON v.video_id = vs.video_id "
            "WHERE vs.date = ? AND vs.status = 'success'",
            (date,),
        )
        return cur.fetchall()

    def upsert_daily_digest(self, date: str, digest_json: str, status: str, notion_page_id: str | None = None) -> None:
        self.conn.execute(
            """
            INSERT INTO daily_digests(date, digest_json, status, created_at, notion_page_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
              digest_json=excluded.digest_json,
              status=excluded.status,
              created_at=excluded.created_at,
              notion_page_id=COALESCE(excluded.notion_page_id, daily_digests.notion_page_id)
            """,
            (date, digest_json, status, datetime.utcnow().isoformat(), notion_page_id),
        )
        self.conn.commit()

    def get_daily_digest(self, date: str) -> sqlite3.Row | None:
        cur = self.conn.execute("SELECT * FROM daily_digests WHERE date = ?", (date,))
        return cur.fetchone()

    def set_notion_page_id(self, date: str, page_id: str) -> None:
        self.conn.execute("UPDATE daily_digests SET notion_page_id = ? WHERE date = ?", (page_id, date))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
