"""
Sketch Engine Bonito API — user + API key (HTTP Basic).

See: https://www.sketchengine.eu/documentation/api-documentation/
Base: https://api.sketchengine.eu/bonito/run.cgi
Respect fair-use / request spacing (FUP) in production.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from pipeline.config import get_settings

BASE = "https://api.sketchengine.eu/bonito/run.cgi"

# Latest large Croatian **web** corpus in Sketch (see e.g. hrWaC page; link uses this id).
# Changelog: hrwac 2.2+ on Sketch — ~1.9B tokens in academic descriptions; this id is the dashboard corpus name.
CROATIAN_WEB_CORPUS_DEFAULT = "preloaded/hrwac22_rft1"


def cql_word_form(keyword: str) -> str:
    """
    CQL for a **token** (word) match in Bonito, e.g. ``q[word="Ustaše"]``.

    Escapes backslashes and double quotes in ``keyword``.
    """
    if not (keyword and str(keyword).strip()):
        raise ValueError("keyword must be non-empty for word-form CQL")
    esc = str(keyword).strip().replace("\\", "\\\\").replace('"', '\\"')
    return f'q[word="{esc}"]'


def _auth() -> tuple[str, str]:
    s = get_settings()
    u, k = s.sketch_engine_user.strip(), s.sketch_engine_key.strip()
    if not u or not k:
        raise RuntimeError("Set SKETCH_ENGINE_USER and SKETCH_ENGINE_KEY in .env")
    return (u, k)


def fetch_corp_info(corpname: str) -> dict:
    """Corpus metadata JSON (validates auth + corpus name)."""
    with httpx.Client(timeout=60.0) as c:
        r = c.get(
            f"{BASE}/corp_info",
            params={"corpname": corpname, "format": "json"},
            auth=_auth(),
            headers={"User-Agent": "SlursPipeline/0.1 (academic research)"},
        )
        r.raise_for_status()
        return r.json()


def fetch_concordance(
    cql: str,
    *,
    corpname: str = CROATIAN_WEB_CORPUS_DEFAULT,
    pagesize: int = 5,
    asyn: int = 0,
) -> dict:
    """
    **view** (concordance) — ``cql`` must be a full Bonito query, e.g. ``q[word=\\"Hrvatska\\"]``.

    Uses synchronous mode (``asyn=0``) so the response returns when lines are ready.
    Respect Sketch Engine FUP: keep ``pagesize`` small for automation.
    """
    if not cql.strip().startswith("q["):
        raise ValueError("CQL must start with q[...] (CQL body). Example: q[word=\"Hrvatska\"]")
    with httpx.Client(timeout=120.0) as c:
        r = c.get(
            f"{BASE}/view",
            params={
                "corpname": corpname,
                "format": "json",
                "asyn": str(asyn),
                "pagesize": str(min(max(pagesize, 1), 100)),
                "q": cql,
            },
            auth=_auth(),
            headers={"User-Agent": "SlursPipeline/0.1 (academic research)"},
        )
        r.raise_for_status()
        return r.json()


def save_corp_info(corpname: str | None = None, out: Path | None = None) -> Path:
    s = get_settings()
    name = (corpname or s.sketch_default_corp).strip()
    data = fetch_corp_info(name)
    out = out or s.data_raw / f"sketch_corp_info_{name.replace('/','_')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2)[:1_000_000], encoding="utf-8")
    return out


def save_concordance_sample(
    cql: str,
    *,
    corpname: str = CROATIAN_WEB_CORPUS_DEFAULT,
    pagesize: int = 5,
    out: Path | None = None,
) -> Path:
    """
    Run ``fetch_concordance`` and write JSON to ``data/raw/`` (concordance + size metadata).
    """
    s = get_settings()
    data = fetch_concordance(cql, corpname=corpname, pagesize=pagesize)
    stem = f"sketch_view_{corpname.replace('/', '_')}"
    out = out or s.data_raw / f"{stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "corpname": corpname,
                "cql": cql,
                "concsize": data.get("concsize"),
                "lines_returned": len(data.get("Lines") or []),
                "view": data,
            },
            ensure_ascii=False,
            indent=2,
        )[:2_000_000],
        encoding="utf-8",
    )
    return out
