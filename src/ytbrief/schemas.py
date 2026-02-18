from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KeyEvent(BaseModel):
    event: str
    why: str


class SectorAsset(BaseModel):
    name: str
    direction: Literal["up", "down", "mixed"]
    why: str


class NumberFact(BaseModel):
    metric: str
    value: str
    context: str


class TickerMention(BaseModel):
    ticker: str
    context: str


class VideoSummary(BaseModel):
    one_liner: str
    market_drivers: list[str] = Field(min_length=3, max_length=3)
    key_events: list[KeyEvent]
    sectors_assets: list[SectorAsset]
    numbers: list[NumberFact]
    tickers_mentions: list[TickerMention]
    what_to_watch: list[str] = Field(min_length=3, max_length=3)
    confidence: Literal["high", "medium", "low"]


class DigestSource(BaseModel):
    title: str
    url: str
    channel: str


class DailyDigest(BaseModel):
    date: str
    one_liner: str
    consensus: list[str] = Field(min_length=3, max_length=3)
    differences: list[str] = Field(min_length=3, max_length=3)
    checklist: list[str] = Field(min_length=3, max_length=3)
    top_topics: list[str]
    sources: list[DigestSource]
