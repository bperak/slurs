"""
Event Registry (NewsAPI.ai) — set EVENTREGISTRY_API_KEY.

Authoritative examples: https://www.newsapi.ai/documentation/examples
Query semantics: https://github.com/EventRegistry/event-registry-python/wiki/Searching-for-articles
Endpoint: POST https://eventregistry.org/api/v1/article/getArticles
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from pipeline.config import get_settings

BASE = "https://eventregistry.org/api/v1/article/getArticles"


def _require_key() -> str:
    s = get_settings()
    k = s.eventregistry_api_key.strip()
    if not k:
        raise RuntimeError("Set EVENTREGISTRY_API_KEY in .env (see README.md).")
    return k


def _post(body: dict) -> dict:
    with httpx.Client(timeout=120.0) as c:
        r = c.post(
            BASE,
            json=body,
            headers={
                "User-Agent": "SlursPipeline/0.1 (academic research)",
                "Content-Type": "application/json",
            },
        )
        r.raise_for_status()
        return r.json()


def fetch_articles(
    keyword: str,
    *,
    lang: str = "eng",
    articles_count: int = 50,
    articles_page: int = 1,
    # Time: use forceMaxDataTimeWindow (days) for *recent* articles (default API behaviour).
    force_max_data_time_window: int = 31,
    # Optional calendar range (YYYY-MM-DD). May return 0 rows if your plan has no archive.
    date_start: str | None = None,
    date_end: str | None = None,
    keyword_loc: str = "body",
    keyword_search_mode: str = "phrase",
    is_duplicate_filter: str = "skipDuplicates",
    data_types: list[str] | None = None,
    include_concepts: bool = False,
    include_categories: bool = False,
    body_max_len: int = 4000,
) -> dict:
    """
    Search news/PR with parameters aligned to Event Registry docs.

    - ``keywordSearchMode``: phrase | simple | exact (see Python SDK / wiki).
    - ``keywordLoc``: body | title | title,body
    - Recent window: ``force_max_data_time_window`` (default 31 days).
    - If both ``date_start`` and ``date_end`` are set, they are sent at the top level
      (same as QueryArticles in the official SDK) *in addition* to the time window
      if you still set ``force_max_data_time_window``; for strict range-only search,
      pass ``force_max_data_time_window=0`` or we omit it when dates are set — we omit
      the window when both dates are provided to avoid contradictions.
    """
    key = _require_key()
    data_types = data_types or ["news", "pr"]
    body: dict[str, Any] = {
        "action": "getArticles",
        "keyword": keyword,
        "lang": lang,
        "articlesPage": articles_page,
        "articlesCount": min(max(1, articles_count), 100),
        "articlesSortBy": "date",
        "articlesSortByAsc": False,
        "resultType": "articles",
        "dataType": data_types,
        "apiKey": key,
        "articlesArticleBodyLen": body_max_len,
        "keywordLoc": keyword_loc,
        "keywordSearchMode": keyword_search_mode,
        "isDuplicateFilter": is_duplicate_filter,
    }
    if date_start and date_end:
        body["dateStart"] = date_start
        body["dateEnd"] = date_end
    else:
        body["forceMaxDataTimeWindow"] = force_max_data_time_window

    if include_concepts:
        body["includeArticleConcepts"] = True
    if include_categories:
        body["includeArticleCategories"] = True

    return _post(body)


def response_to_table_rows(data: dict) -> list[dict[str, Any]]:
    """Flatten article results for CSV / evidence tables."""
    out: list[dict[str, Any]] = []
    for a in data.get("articles", {}).get("results") or []:
        src = a.get("source") or {}
        text = a.get("body") or ""
        out.append(
            {
                "date": a.get("date"),
                "date_time_utc": a.get("dateTime"),
                "title": a.get("title"),
                "url": a.get("url"),
                "lang": a.get("lang"),
                "source_domain": src.get("uri"),
                "source_name": src.get("title"),
                "is_duplicate": a.get("isDuplicate"),
                "data_type": a.get("dataType"),
                "body_excerpt": text[:3000] if text else "",
            }
        )
    return out


def save_evidence(
    keyword: str,
    out_json: Path | None = None,
    *,
    lang: str = "eng",
    count: int = 30,
    csv_also: bool = True,
    file_stem: str | None = None,
    **kwargs: Any,
) -> tuple[Path, Path | None]:
    """
    Run ``fetch_articles``, write full JSON and optional CSV of flattened rows.
    Returns (json_path, csv_path_or_none).

    ``file_stem``: optional stable id (e.g. ``eng_libtard``) for batch runs instead of
    deriving the filename from the keyword.
    """
    data = fetch_articles(keyword, lang=lang, articles_count=count, **kwargs)
    settings = get_settings()
    if file_stem:
        stem = "".join(c if c.isalnum() or c in " -_" else "_" for c in file_stem)[:100].strip()
        stem = "_".join(stem.split()) or "query"
        base = settings.data_raw / f"eventregistry_evidence_{stem}"
    else:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in keyword)[:80].strip() or "query"
        safe = "_".join(safe.split())  # no spaces in filenames
        base = settings.data_raw / f"eventregistry_evidence_{safe}_{lang}"
    jpath = out_json or base.with_suffix(".json")
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2)[:2_000_000], encoding="utf-8")

    cpath: Path | None = None
    if csv_also:
        rows = response_to_table_rows(data)
        cpath = base.with_suffix(".csv")
        pd.DataFrame(rows).to_csv(cpath, index=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL)
    return jpath, cpath


# --- Backwards compatibility ---

def fetch_articles_sample(
    keyword: str = "test",
    *,
    lang: str = "eng",
    articles_count: int = 5,
) -> dict:
    return fetch_articles(
        keyword,
        lang=lang,
        articles_count=articles_count,
        force_max_data_time_window=31,
    )


def save_sample(
    keyword: str = "test",
    out: Path | None = None,
    *,
    lang: str = "eng",
) -> Path:
    data = fetch_articles_sample(keyword, lang=lang, articles_count=5)
    settings = get_settings()
    safe = "".join(c if c.isalnum() else "_" for c in keyword)[:60]
    out = out or settings.data_raw / f"eventregistry_{safe}_{lang}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2)[:500_000], encoding="utf-8")
    return out
