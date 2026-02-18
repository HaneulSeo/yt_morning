from __future__ import annotations

import json
import random
import time

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover
    from . import requests_compat as requests
from pydantic import ValidationError

from .schemas import DailyDigest, VideoSummary


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro", session: requests.Session | None = None):
        self.api_key = api_key
        self.model = model
        self.session = session or requests.Session()

    @property
    def endpoint(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def summarize_video(self, url: str) -> VideoSummary:
        prompt = (
            "Analyze this YouTube morning market briefing video URL and return STRICT JSON ONLY with no markdown.\n"
            f"URL: {url}\n"
            "Schema: "
            '{"one_liner": string, "market_drivers": [string,string,string], '
            '"key_events": [{"event": string, "why": string}], '
            '"sectors_assets": [{"name": string, "direction": "up|down|mixed", "why": string}], '
            '"numbers": [{"metric": string, "value": string, "context": string}], '
            '"tickers_mentions": [{"ticker": string, "context": string}], '
            '"what_to_watch": [string,string,string], "confidence": "high|medium|low"}'
        )
        text = self._generate_text(prompt)
        try:
            return VideoSummary.model_validate_json(text)
        except ValidationError:
            repair_prompt = (
                "Your previous output was invalid. Output STRICT JSON ONLY that matches exactly this schema. "
                "Do not include code fences or explanations."
            )
            repaired = self._generate_text(repair_prompt + "\nOriginal output:\n" + text)
            return VideoSummary.model_validate_json(repaired)

    def build_daily_digest(self, date: str, per_video_json: list[dict]) -> DailyDigest:
        prompt = (
            "Create a consolidated daily market digest in Korean from these video summaries."
            " Return STRICT JSON ONLY, no markdown.\n"
            f"date={date}\n"
            f"summaries={json.dumps(per_video_json, ensure_ascii=False)}\n"
            "Schema: "
            '{"date":"YYYY-MM-DD","one_liner":string,"consensus":[string,string,string],'
            '"differences":[string,string,string],"checklist":[string,string,string],'
            '"top_topics":[string],"sources":[{"title":string,"url":string,"channel":string}]}'
        )
        text = self._generate_text(prompt)
        try:
            return DailyDigest.model_validate_json(text)
        except ValidationError:
            repaired = self._generate_text(
                "Fix this to valid JSON matching schema exactly. JSON only.\n" + text
            )
            return DailyDigest.model_validate_json(repaired)

    def _generate_text(self, prompt: str, max_retries: int = 3) -> str:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        params = {"key": self.api_key}
        for attempt in range(max_retries):
            resp = self.session.post(self.endpoint, params=params, json=payload, timeout=120)
            if resp.status_code < 400:
                data = resp.json()
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError) as exc:
                    raise ValueError(f"Invalid Gemini response: {data}") from exc
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep((2**attempt) + random.uniform(0.5, 1.5))
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return ""
