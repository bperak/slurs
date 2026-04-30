"""Batch Wikipedia pageviews (no key) from config/wiki_pageviews.json."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from pipeline.config import get_settings
from pipeline.ingest import wikipedia

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "wiki_pageviews.json"


def run_wiki_batch(config_path: Path = DEFAULT_CONFIG) -> list[Path]:
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    s = get_settings()
    out_paths: list[Path] = []
    for p in cfg.get("pages", []):
        project = p["project"]
        title = p["title"]
        days = int(p.get("days", 30))
        end = date.today()
        start = end - timedelta(days=days)
        pid = (p.get("id") or "").strip()
        if pid:
            out = s.data_raw / f"wiki_batch_{pid}.json"
        else:
            out = None
        path = wikipedia.save_pageviews_json(project, title, start, end, out=out)
        out_paths.append(path)
    return out_paths
