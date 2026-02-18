# ytbrief

`ytbrief` is an end-to-end Python CLI MVP that creates a **daily Korean market morning digest** by:

1. Searching YouTube videos uploaded on a given date (Asia/Seoul)
2. Summarizing each video with Gemini (one URL per request)
3. Building one consolidated daily digest JSON
4. Upserting one Notion database page for that date

> It is idempotent: rerunning the same date updates existing SQLite rows and Notion page rather than duplicating.

## Features

- CLI with Typer (`ytbrief fetch/summarize/digest/publish-notion/run`)
- YouTube Data API search.list integration with Korean keywords
- Gemini strict-JSON summarization with one repair retry on invalid JSON
- Notion upsert by Date property and full children block replacement
- SQLite persistence for videos, per-video summaries, and daily digest
- Rich progress/logging and retry with backoff + jitter

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

Verify command:

```bash
ytbrief --help
```

## Required environment variables

Required:

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY`
- `NOTION_TOKEN`
- `NOTION_DATABASE_ID`

Optional:

- `GEMINI_MODEL` (default: `gemini-1.5-pro`)
- `NOTION_VERSION` (default: `2022-06-28`)
- `TZ` (recommend `Asia/Seoul`)

You can use a `.env` file in project root:

```env
YOUTUBE_API_KEY=...
GEMINI_API_KEY=...
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=...
GEMINI_MODEL=gemini-1.5-pro
NOTION_VERSION=2022-06-28
TZ=Asia/Seoul
```

## API setup

### 1) YouTube API key

1. Open Google Cloud Console
2. Enable **YouTube Data API v3**
3. Create API key and restrict it as needed
4. Export as `YOUTUBE_API_KEY`

### 2) Notion integration + DB

1. Create a Notion internal integration and copy token
2. Create (or choose) a Notion database
3. Share database with the integration
4. Set database properties exactly:
   - `Name` (title)
   - `Date` (date)
   - `VideoCount` (number)
   - `Summary` (rich_text)
   - `Topics` (multi_select)
   - `Confidence` (select with options: `high`, `medium`, `low`)
5. Copy DB id to `NOTION_DATABASE_ID`

## CLI usage

```bash
ytbrief fetch --date YYYY-MM-DD --limit 20 --db ytbrief.db
ytbrief summarize --date YYYY-MM-DD --db ytbrief.db
ytbrief digest --date YYYY-MM-DD --db ytbrief.db
ytbrief publish-notion --date YYYY-MM-DD --db ytbrief.db
```

All-in-one run:

```bash
ytbrief run --date 2026-02-19 --db ytbrief.db
```

Pipeline order for `run`:

`fetch -> summarize -> digest -> publish-notion`

## YouTube discovery behavior

- Uses `search.list`
- Keywords:
  - 모닝브리핑
  - 장전 시황
  - 오늘 시황
  - 미국증시
  - 증시 브리핑
  - 뉴욕증시
  - 시장 브리핑
- Window:
  - `publishedAfter = date 00:00:00+09:00`
  - `publishedBefore = date+1 00:00:00+09:00`
- Filters:
  - `type=video`
  - `videoCaption=closedCaption`

## Data model (SQLite)

- `videos(video_id TEXT PRIMARY KEY, date TEXT, title TEXT, channel TEXT, published_at TEXT, url TEXT, fetched_at TEXT)`
- `video_summaries(video_id TEXT, date TEXT, summary_json TEXT, status TEXT, created_at TEXT, PRIMARY KEY(video_id, date))`
- `daily_digests(date TEXT PRIMARY KEY, digest_json TEXT, status TEXT, created_at TEXT, notion_page_id TEXT)`

## Notes about Notion content

- Full transcripts are **not** stored.
- Only derived summaries / digest JSON / links are used.
- Children blocks include:
  - 오늘 한줄
  - 컨센서스
  - 관점 차이
  - 체크리스트
  - Sources

## Troubleshooting

- **401 / 403 from YouTube**
  - API key missing, invalid, or API not enabled.
- **Notion 401 unauthorized**
  - Wrong token or integration not connected.
- **Notion "object_not_found" / invalid DB ID**
  - Database ID is wrong or DB not shared with integration.
- **No videos found**
  - Date may have no matching uploads with captions; try higher `--limit` or different date.
- **Gemini JSON validation errors**
  - App retries once with repair prompt; failures are stored with `status=failed` and pipeline continues.

## Extend later

- Channel whitelist / blacklist rules
- Weekly digest generation from daily digests
- Slack alert after successful Notion publish
