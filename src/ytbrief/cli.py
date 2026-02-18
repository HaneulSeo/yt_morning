from __future__ import annotations

import logging
import os
from datetime import date as date_type

import typer
from dotenv import load_dotenv
from rich.console import Console

from .logic import create_digest, fetch_videos, publish_notion, run_pipeline, summarize_videos

app = typer.Typer(help="YouTube morning brief -> Gemini digest -> Notion publisher")
console = Console()


def _setup() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler()])


def _validate_date(date: str) -> str:
    date_type.fromisoformat(date)
    return date


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-1.5-pro")


@app.command("fetch")
def fetch_cmd(date: str = typer.Option(..., "--date"), limit: int = typer.Option(20, "--limit"), db: str = typer.Option("ytbrief.db", "--db")):
    _setup()
    date = _validate_date(date)
    count = fetch_videos(db, date, limit)
    console.print(f"[green]Fetched {count} videos for {date}[/green]")


@app.command("summarize")
def summarize_cmd(date: str = typer.Option(..., "--date"), db: str = typer.Option("ytbrief.db", "--db")):
    _setup()
    date = _validate_date(date)
    ok, failed = summarize_videos(db, date, _gemini_model())
    console.print(f"[green]Summaries success={ok} failed={failed}[/green]")


@app.command("digest")
def digest_cmd(date: str = typer.Option(..., "--date"), db: str = typer.Option("ytbrief.db", "--db")):
    _setup()
    date = _validate_date(date)
    status = create_digest(db, date, _gemini_model())
    console.print(f"[green]Digest status={status}[/green]")


@app.command("publish-notion")
def publish_cmd(date: str = typer.Option(..., "--date"), db: str = typer.Option("ytbrief.db", "--db")):
    _setup()
    date = _validate_date(date)
    page_id = publish_notion(db, date)
    console.print(f"[green]Published/updated Notion page={page_id}[/green]")


@app.command("run")
def run_cmd(
    date: str = typer.Option(..., "--date"),
    limit: int = typer.Option(20, "--limit"),
    db: str = typer.Option("ytbrief.db", "--db"),
):
    _setup()
    date = _validate_date(date)
    result = run_pipeline(db, date, limit, _gemini_model())
    console.print(
        "[bold cyan]Pipeline summary[/bold cyan]\n"
        f"videos_found={result.found}\n"
        f"summarized_success={result.summarized_success}\n"
        f"summarized_failed={result.summarized_failed}\n"
        f"digest_status={result.digest_status}\n"
        f"notion_page_id={result.notion_page_id}"
    )


if __name__ == "__main__":
    app()
