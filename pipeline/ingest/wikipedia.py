"""Wikimedia pageviews — no API key. https://wikimedia.org/api/rest_v1/ """

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

from pipeline.config import get_settings


def fetch_pageviews(
    project: str,
    title: str,
    start: date,
    end: date,
    *,
    client: httpx.Client | None = None,
) -> dict:
    """
    Daily pageviews for a single article. project e.g. 'en.wikipedia' or 'hr.wikipedia'.
    """
    # format YYYYMMDD
    s = start.strftime("%Y%m%d")
    e = end.strftime("%Y%m%d")
    # Path order: project / access / agent / ARTICLE / granularity / start / end
    # (see https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/examples/page-metrics.html)
    enc = quote(title.replace(" ", "_"), safe="")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{project}/all-access/all-agents/{enc}/daily/{s}/{e}"
    )
    own = client is None
    c = client or httpx.Client(timeout=30.0)
    try:
        r = c.get(url, headers={"User-Agent": "SlursPipeline/0.1 (research; contact: academic)"})
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            c.close()


def save_pageviews_json(
    project: str, title: str, start: date, end: date, out: Path | None = None
) -> Path:
    data = fetch_pageviews(project, title, start, end)
    settings = get_settings()
    if out is None:
        safe = title.replace("/", "-")[:80]
        out = settings.data_raw / f"wiki_{project}_{safe}_{start}_{end}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
