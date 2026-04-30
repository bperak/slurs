"""
GDELT GKG on Google BigQuery — optional **news-scale** cross-check of theme text in ``V2Themes``.

Requires: ``pip install -e ".[gdelt]"`` and ``GOOGLE_CLOUD_PROJECT`` plus
Application Default Credentials or a service account JSON
(``GOOGLE_APPLICATION_CREDENTIALS``).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pipeline.config import get_settings

CONFIG_DEFAULT = Path(__file__).resolve().parent.parent.parent / "config" / "gdelt_queries.json"


def _sanitize_substrings(subs: list[str], *, max_n: int = 8) -> list[str]:
    out: list[str] = []
    for s in subs[:max_n]:
        t = s.strip().lower()
        t = re.sub(r"[^a-z0-9 \u00c0-\u024f-]+", " ", t)
        t = " ".join(t.split())
        if len(t) >= 2 and t not in out:
            out.append(t)
    return out


def _where_theme_likes(subs: list[str]) -> str:
    if not subs:
        return "FALSE"
    parts: list[str] = []
    for s in subs:
        t = s.replace("'", "''")
        parts.append(f"LOWER(COALESCE(V2Themes, '')) LIKE '%{t}%'")
    return "(" + " OR ".join(parts) + ")"


def _partition_range(partition_start: str, partition_end: str) -> tuple[datetime, datetime]:
    d0 = date.fromisoformat(partition_start.strip())
    d1 = date.fromisoformat(partition_end.strip()) + timedelta(days=1)
    a = datetime(d0.year, d0.month, d0.day, tzinfo=timezone.utc)
    b = datetime(d1.year, d1.month, d1.day, tzinfo=timezone.utc)
    return a, b


def run_gdelt_snapshot(
    config_path: Path | None = None,
    *,
    project: str | None = None,
) -> Path:
    from google.cloud import bigquery

    s = get_settings()
    project = (project or s.google_cloud_project or "").strip()
    if not project:
        raise RuntimeError("Set GOOGLE_CLOUD_PROJECT in .env for BigQuery (GDELT).")

    cfgp = config_path or CONFIG_DEFAULT
    cfg = json.loads(cfgp.read_text(encoding="utf-8"))
    table = (cfg.get("table") or "gdelt-bq.gdeltv2.gkg_partitioned").strip()
    runs_in = cfg.get("runs") or []
    if not runs_in:
        raise ValueError("No runs in gdelt config.")

    bq_client = bigquery.Client(project=project)
    out_runs: list[dict[str, Any]] = []

    for r in runs_in:
        rid = r.get("id", "run")
        label = r.get("label", "")
        d0 = (r.get("partition_start") or "").strip()
        d1e = (r.get("partition_end") or "").strip()
        subs = _sanitize_substrings(list(r.get("theme_substrings") or []))
        if not d0 or not d1e or not subs:
            out_runs.append(
                {
                    "id": rid,
                    "label": label,
                    "error": "missing partition_start, partition_end, or theme_substrings",
                    "gkg_record_count_theme_match": None,
                }
            )
            continue
        try:
            t0, t1 = _partition_range(d0, d1e)
        except ValueError as e:
            out_runs.append({"id": rid, "label": label, "error": str(e), "gkg_record_count_theme_match": None})
            continue
        like_sql = _where_theme_likes(subs)
        full_sql = f"""
SELECT COUNT(*) AS c
FROM `{table}`
WHERE _PARTITIONTIME >= @t0
  AND _PARTITIONTIME < @t1
  AND {like_sql}
"""
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0),
                bigquery.ScalarQueryParameter("t1", "TIMESTAMP", t1),
            ]
        )
        err: str | None = None
        n: int | None = None
        job_bytes: int | None = None
        try:
            job = bq_client.query(full_sql, job_config=job_config, location="US")
            rows = list(job.result(timeout=300))
            n = int(rows[0].c) if rows else 0
            if job.total_bytes_processed is not None:
                job_bytes = int(job.total_bytes_processed)
        except Exception as e:
            err = str(e)[:1200]
        out_runs.append(
            {
                "id": rid,
                "label": label,
                "partition_start": d0,
                "partition_end": d1e,
                "theme_substrings": subs,
                "gkg_record_count_theme_match": n,
                "total_bytes_processed": job_bytes,
                "error": err,
            }
        )

    summary: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "config": str(cfgp.resolve()),
        "table": table,
        "runs": out_runs,
        "caveat": "Coarse GKG V2Themes substring row count. Not de-duplicated by article; not comparable to Trends 0–100.",
    }
    out = s.data_processed / f"gdelt_summary_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


__all__ = ["run_gdelt_snapshot", "CONFIG_DEFAULT"]
