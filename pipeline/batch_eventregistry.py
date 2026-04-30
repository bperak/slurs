"""Run Event Registry evidence pulls for every entry in config/slurs_terms.json."""

from __future__ import annotations

import json
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pipeline.config import get_settings
from pipeline.ingest import eventregistry
from pipeline.summarize import write_summary_csv

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "slurs_terms.json"


def _load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_batch(
    config_path: Path = DEFAULT_CONFIG,
    *,
    dry_run: bool = False,
    summarize_after: bool = True,
) -> Path:
    """
    For each query in config: ``save_evidence`` with id as ``file_stem``.
    Writes ``data/raw/batch_run_<ts>.log.json`` with status per query.
    """
    cfg = _load_config(config_path)
    defaults = cfg.get("eventregistry_defaults") or {}
    sleep_s = float(cfg.get("sleep_seconds_between_requests", 2.0))
    queries: list[dict] = list(cfg.get("queries") or [])
    s = get_settings()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log: dict[str, Any] = {
        "run_id": run_id,
        "date": date.today().isoformat(),
        "config": str(config_path),
        "ok": True,
        "items": [],
    }
    if not s.has_eventregistry and not dry_run:
        log["ok"] = False
        log["skipped"] = (
            "No EVENTREGISTRY_API_KEY. Use a free key from newsapi.ai (limited last-30d + token cap) "
            "or run a fully free path: python -m pipeline run-free"
        )
        log_path = s.data_raw / f"batch_run_{run_id}.log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        return log_path
    for i, q in enumerate(queries):
        qid = (q.get("id") or "").strip() or f"q_{i}"
        keyword = (q.get("keyword") or "").strip()
        lang = (q.get("lang") or "eng").strip()
        if not keyword:
            log["items"].append({"id": qid, "error": "empty keyword", "ok": False})
            log["ok"] = False
            continue
        if dry_run:
            log["items"].append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "ok": True,
                    "dry_run": True,
                }
            )
            continue
        try:
            jpath, cpath = eventregistry.save_evidence(
                keyword,
                lang=lang,
                count=int(defaults.get("count", 25)),
                csv_also=True,
                file_stem=qid,
                force_max_data_time_window=int(defaults.get("window_days", 31)),
                keyword_search_mode=str(defaults.get("mode", "phrase")),
                keyword_loc=str(defaults.get("loc", "body")),
            )
            log["items"].append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "ok": True,
                    "json": str(jpath),
                    "csv": str(cpath) if cpath else None,
                }
            )
        except Exception as e:  # noqa: BLE001
            log["ok"] = False
            log["items"].append(
                {
                    "id": qid,
                    "keyword": keyword,
                    "lang": lang,
                    "ok": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()[-2000:],
                }
            )
        if not dry_run and i < len(queries) - 1:
            time.sleep(sleep_s)
    log_path = s.data_raw / f"batch_run_{run_id}.log.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    if summarize_after and not dry_run and log["items"]:
        try:
            write_summary_csv()
        except Exception as e:  # noqa: BLE001
            log["summarize_error"] = str(e)
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path
