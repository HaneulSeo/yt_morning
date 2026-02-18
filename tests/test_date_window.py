from ytbrief.youtube_client import YouTubeClient


def test_seoul_date_window_iso():
    start, end = YouTubeClient.seoul_date_window("2026-02-19")
    assert start == "2026-02-19T00:00:00+09:00"
    assert end == "2026-02-20T00:00:00+09:00"
