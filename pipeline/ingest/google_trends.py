"""
Unofficial Google Trends (relative search interest) via ``pytrends``.

- No API key. Not an official API; use for **illustration** alongside Event Registry, not as ground truth.
- **Relative** 0–100 scale per request batch; you cannot compare absolute levels across two separate ``build_payload`` calls.
- Hate / slur queries may return **all zeros** (data withheld / low volume).

Install: ``pip install -e ".[trends]"`` from the project root.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.config import get_settings

# --- optional dependency ---
def _trendreq():
    try:
        from pytrends.request import TrendReq  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError(
            "Install the trends extra: pip install -e '.[trends]'  (pytrends + lxml)"
        ) from e
    return TrendReq


def _slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:80] or "run"


@dataclass
class TrendRun:
    id: str
    label: str
    timeframe: str
    geo: str
    event_date: str
    keywords: list[str]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TrendRun":
        kws = d.get("keywords") or []
        if len(kws) > 5:
            kws = kws[:5]
        return cls(
            id=d["id"],
            label=d.get("label", ""),
            timeframe=d["timeframe"],
            geo=d.get("geo", ""),
            event_date=d.get("event_date", ""),
            keywords=kws,
        )


def interest_over_time(
    run: TrendRun, *, hl: str | None = None, tz: int = 120
) -> pd.DataFrame:
    """Return daily (or weekly) interest-over-time for up to 5 ``keywords``."""
    if hl is None:
        hl = "hr" if (run.geo or "").upper() in ("HR", "BA", "RS", "ME") else "en-US"
    from pytrends import exceptions as pyt_exc  # type: ignore[import-not-found]

    TrendReq = _trendreq()
    pyt = TrendReq(hl=hl, tz=tz)
    if not run.keywords:
        raise ValueError("keywords required (max 5).")
    last: Exception | None = None
    for attempt in range(4):
        try:
            pyt.build_payload(run.keywords, timeframe=run.timeframe, geo=run.geo)
            df = pyt.interest_over_time()
            break
        except pyt_exc.TooManyRequestsError as e:
            last = e
            if attempt >= 3:
                raise
            time.sleep(15.0 * (2**attempt))
    else:
        raise last or RuntimeError("Trends: no data")
    if df is None or df.empty:
        return pd.DataFrame()
    if "isPartial" in df.columns:
        df = df.drop(columns=["isPartial"])
    return df


def add_event_ratio(
    df: pd.DataFrame,
    event_date: str,
    *,
    window_days: int = 3,
) -> dict[str, Any]:
    """
    Heuristic: for each term, max value in [event - window, event + window] vs
    mean of the rest. Only meaningful for **one** run's relative scale.
    """
    if df.empty or not event_date:
        return {}
    try:
        ed = pd.Timestamp(event_date)
    except ValueError:
        return {"error": "invalid event_date"}
    idx = pd.to_datetime(df.index, utc=False)
    df2 = df.copy()
    mask = (idx >= ed - pd.Timedelta(days=window_days)) & (
        idx <= ed + pd.Timedelta(days=window_days)
    )
    out: dict[str, Any] = {"event_date": event_date, "window_days": window_days, "by_keyword": {}}
    for col in df2.columns:
        series = df2[col].astype(float)
        event_slice = float(series.loc[mask].max()) if mask.any() else 0.0
        rest = float(series.loc[~mask].mean()) if (~mask).any() else 1.0
        if rest < 0.1:
            rest = 0.1
        out["by_keyword"][col] = {
            "max_around_event": event_slice,
            "mean_outside": round(rest, 4),
            "ratio": round(event_slice / rest, 3),
        }
    return out


def write_trend_run_outputs(run: TrendRun, df: pd.DataFrame) -> list[Path]:
    """Write CSV + JSON summary for one ``TrendRun`` to ``data/processed/``."""
    s = get_settings()
    stem = _slug(run.id)
    pdir = s.data_processed
    pdir.mkdir(parents=True, exist_ok=True)
    p_csv = pdir / f"trends_iot_{stem}.csv"
    p_json = pdir / f"trends_summary_{stem}.json"
    if not df.empty:
        df.to_csv(p_csv, encoding="utf-8")
    else:
        p_csv.write_text("date\n", encoding="utf-8")
    meta = {
        "run": run.__dict__,
        "n_rows": int(len(df)),
        "spike": add_event_ratio(df, run.event_date) if not df.empty else {},
        "caveat": "Relative 0-100 in this request only. Not comparable across different build_payload calls.",
    }
    p_json.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return [p_csv, p_json]


def run_custom_window(
    *,
    run_id: str,
    label: str,
    start: date,
    end: date,
    geo: str,
    event_date: str,
    keywords: list[str],
) -> list[Path]:
    """
    Google Trends for an arbitrary **calendar** window (e.g. ±N days around an event).
    At most 5 ``keywords``. ``event_date`` is used for the spike ratio in the JSON summary.
    """
    kws = [k.strip() for k in keywords if k.strip()][:5]
    if not kws:
        raise ValueError("At least one keyword is required (max 5).")
    tf = f"{start:%Y-%m-%d} {end:%Y-%m-%d}"
    run = TrendRun(
        id=run_id,
        label=label,
        timeframe=tf,
        geo=geo,
        event_date=event_date,
        keywords=kws,
    )
    df = interest_over_time(run)
    return write_trend_run_outputs(run, df)


def run_from_config(
    path: Path | None = None,
    run_id: str | None = None,
    *,
    sleep_s: float = 6.0,
) -> list[Path]:
    """
    Load ``config/trends_event_windows.json``, run each (or one ``run_id``),
    write Parquet/CSV and JSON summary to ``data/processed/``.
    """
    base = path or (Path(__file__).resolve().parent.parent.parent / "config" / "trends_event_windows.json")
    cfg = json.loads(base.read_text(encoding="utf-8"))
    runs = [TrendRun.from_dict(r) for r in cfg.get("runs", [])]
    if run_id:
        runs = [r for r in runs if r.id == run_id]
    if not runs:
        raise ValueError("No runs selected.")

    out_paths: list[Path] = []
    for i, run in enumerate(runs):
        if i:
            time.sleep(sleep_s)
        df = interest_over_time(run)
        out_paths.extend(write_trend_run_outputs(run, df))
    return out_paths


__all__ = [
    "TrendRun",
    "interest_over_time",
    "add_event_ratio",
    "run_from_config",
    "run_custom_window",
    "write_trend_run_outputs",
]
