import json

from ytbrief.storage import Storage


def test_sqlite_upsert(tmp_path):
    db = tmp_path / "t.db"
    store = Storage(str(db))

    row = {
        "video_id": "abc",
        "date": "2026-02-19",
        "title": "제목",
        "channel": "채널",
        "published_at": "2026-02-19T01:00:00Z",
        "url": "https://youtube.com/watch?v=abc",
        "fetched_at": "now",
    }
    store.upsert_video(row)
    row["title"] = "새제목"
    store.upsert_video(row)

    videos = store.list_videos_by_date("2026-02-19")
    assert len(videos) == 1
    assert videos[0]["title"] == "새제목"

    store.upsert_video_summary("abc", "2026-02-19", json.dumps({"one_liner": "x"}), "success")
    store.upsert_video_summary("abc", "2026-02-19", json.dumps({"one_liner": "y"}), "success")
    rows = store.list_successful_summaries("2026-02-19")
    assert len(rows) == 1
    assert json.loads(rows[0]["summary_json"])["one_liner"] == "y"

    store.close()
