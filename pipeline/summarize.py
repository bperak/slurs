"""Build summary tables from saved Event Registry JSON under data/raw/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.config import get_settings


def _parse_evidence_file(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or not path.name.startswith("eventregistry_evidence_"):
        return None
    if not path.suffix == ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8")[:2_000_000])
    except (json.JSONDecodeError, OSError):
        return None
    art = data.get("articles") or {}
    return {
        "file": str(path),
        "stem": path.stem,
        "total_results": art.get("totalResults"),
        "returned_in_page": art.get("count"),
        "page": art.get("page"),
        "pages": art.get("pages"),
        "api_info": (data.get("info") or "")[:500],
    }


def summarize_eventregistry_raw(
    raw_dir: Path | None = None,
) -> pd.DataFrame:
    """One row per ``eventregistry_evidence_*.json`` file in ``raw_dir``."""
    s = get_settings()
    raw_dir = raw_dir or s.data_raw
    rows: list[dict[str, Any]] = []
    for p in sorted(raw_dir.glob("eventregistry_evidence_*.json")):
        row = _parse_evidence_file(p)
        if row:
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["file", "stem", "total_results", "returned_in_page", "api_info"])
    return pd.DataFrame(rows)


def write_summary_csv(
    out: Path | None = None,
    *,
    raw_dir: Path | None = None,
) -> Path:
    s = get_settings()
    out = out or s.data_processed / "eventregistry_summary.csv"
    df = summarize_eventregistry_raw(raw_dir=raw_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    return out


def extract_keyword_lang_from_stem(stem: str) -> tuple[str, str] | None:
    """
    Best-effort: stems like ``eventregistry_evidence_hrv_klerofasist`` -> keyword hint.
    Returns (id_or_key, lang_guess) or None.
    """
    m = re.match(r"^eventregistry_evidence_(.+)$", stem)
    if not m:
        return None
    rest = m.group(1)
    if rest.startswith(("eng_", "hrv_")):
        return rest, rest[:3]
    return rest, "?"
