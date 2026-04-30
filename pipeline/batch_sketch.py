"""Run Sketch Engine (hrWac) **word-form** concordance counts for terms in slurs_terms.json.

Respects FUP: small pagesize, spacing between calls (``sleep_seconds_between_requests`` in config).
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.config import get_settings
from pipeline.ingest import sketchengine

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "slurs_terms.json"


def _load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _line_kwic_to_str(line: dict[str, Any]) -> str:
    if not line:
        return ""
    out: list[str] = []
    for key in ("Left", "Kwic", "Right"):
        for seg in line.get(key) or []:
            if isinstance(seg, dict):
                out.append(seg.get("str") or "")
    s = "".join(out).replace("\n", " ").strip()
    return s[:_MAX_KWIC] + ("…" if len(s) > _MAX_KWIC else "")


_MAX_KWIC = 400


def run_hrwac_slurs(
    config_path: Path,
    *,
    corpname: str | None = None,
    pagesize: int = 3,
    lang_filter: str = "hrv",
    dry_run: bool = False,
) -> Path:
    """
    For each matching query: ``view`` (concordance) with CQL ``q[word="..."]``;
    writes ``data/processed/sketch_hrwac_slurs.json`` (and timestamped copy).

    *lang_filter:* ``hrv`` = only Croatian terms (default for this corpus);
    ``eng`` = only English; ``all`` = every term.
    """
    if lang_filter not in ("hrv", "eng", "all"):
        raise ValueError("lang_filter must be hrv, eng, or all")
    s = get_settings()
    cfg = _load_config(config_path)
    sleep_s = float(cfg.get("sleep_seconds_between_requests", 2.0))
    # Croatian slur terms require hrWac, not the generic SKETCH_DEFAULT_CORP (e.g. BNC).
    corp = (corpname or sketchengine.CROATIAN_WEB_CORPUS_DEFAULT).strip()
    if not s.has_sketch and not dry_run:
        out = s.data_processed / "sketch_hrwac_slurs.json"
        payload = {
            "version": 1,
            "ok": False,
            "date": date.today().isoformat(),
            "config": str(config_path),
            "corpname": corp,
            "note": "Set SKETCH_ENGINE_USER and SKETCH_ENGINE_KEY in .env",
            "items": [],
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return out
    items_out: list[dict[str, Any]] = []
    n_request = 0
    for i, q in enumerate(list(cfg.get("queries") or [])):
        qid = (q.get("id") or "").strip() or f"q_{i}"
        keyword = (q.get("keyword") or "").strip()
        lang = (q.get("lang") or "eng").strip().lower()
        if not keyword:
            continue
        if lang_filter == "hrv" and lang != "hrv":
            continue
        if lang_filter == "eng" and lang != "eng":
            continue
        cql = sketchengine.cql_word_form(keyword)
        if dry_run:
            items_out.append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "cql": cql,
                    "ok": True,
                    "dry_run": True,
                }
            )
            continue
        try:
            if n_request > 0:
                time.sleep(sleep_s)
            n_request += 1
            data = sketchengine.fetch_concordance(
                cql, corpname=corp, pagesize=pagesize
            )
            lines = data.get("Lines") or []
            size = data.get("concsize")
            if size is not None and not isinstance(size, (int, float)):
                try:
                    size = int(str(size).replace(" ", ""))
                except (TypeError, ValueError):
                    size = None
            if isinstance(size, float) and size.is_integer():
                size = int(size)
            samples: list[str] = []
            for li in lines[: min(len(lines), pagesize)]:
                s_line = _line_kwic_to_str(li if isinstance(li, dict) else {})
                if s_line:
                    samples.append(s_line)
            items_out.append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "cql": cql,
                    "note": (q.get("note") or "").strip(),
                    "concsize": size,
                    "pagesize": pagesize,
                    "lines_returned": len(lines),
                    "sample_kwic": samples,
                    "ok": True,
                }
            )
        except Exception as e:  # noqa: BLE001
            items_out.append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "cql": cql,
                    "ok": False,
                    "error": str(e),
                    "trace": traceback.format_exc()[-2000:],
                }
            )

    out_main = s.data_processed / "sketch_hrwac_slurs.json"
    out_main.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    full: dict[str, Any] = {
        "version": 1,
        "ok": all(x.get("ok", True) for x in items_out) if items_out else True,
        "date": date.today().isoformat(),
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "config": str(config_path),
        "corpname": corp,
        "lang_filter": lang_filter,
        "pagesize": max(1, min(pagesize, 30)),
        "cql_type": "word (surface form) — not lemma; unreferenced digitised web text in hrWaC 2.2+",
        "items": items_out,
    }
    if dry_run:
        full["ok"] = True
        full["dry_run"] = True
    out_main.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    ts = now.strftime("%Y-%m-%dT%H%M%SZ")
    ts_path = s.data_processed / f"sketch_hrwac_slurs_{ts}.json"
    ts_path.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_main
