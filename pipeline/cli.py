"""CLI: doctor (env check), wikipedia pageviews, eventregistry sample."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import typer

from pipeline import __version__
from pipeline import batch_eventregistry, batch_sketch, refresh_output, summarize, wiki_batch
from pipeline.config import get_settings
from pipeline.ingest import eventregistry, sketchengine, wikipedia

app = typer.Typer(help="Slurs / polarization empirical pipeline")


@app.command()
def doctor() -> None:
    """Print which credentials are present (values are not shown)."""
    s = get_settings()
    typer.echo(f"slurs-pipeline {__version__}")
    typer.echo(f"Data dir: {s.pipeline_data_dir}")
    typer.echo(f"EVENTREGISTRY_API_KEY: {'set' if s.has_eventregistry else 'missing'}")
    typer.echo(
        f"Google (BigQuery/GDelt): "
        f"{'credentials or project set' if s.has_gcp else 'missing (optional)'}"
    )
    typer.echo(f"YOUTUBE_DATA_API_KEY: {'set' if s.youtube_data_api_key.strip() else 'missing (optional)'}")
    typer.echo(f"OPENAI_API_KEY: {'set' if s.openai_api_key.strip() else 'missing (optional)'}")
    typer.echo(
        f"SKETCH_ENGINE (user+key): {'set' if s.has_sketch else 'missing (optional)'}; "
        f"default corp: {s.sketch_default_corp!r}"
    )
    bq = "not installed"
    try:
        import google.cloud.bigquery  # noqa: F401

        bq = "google-cloud-bigquery import ok"
    except ImportError:
        pass
    typer.echo(
        f"GOOGLE_CLOUD_PROJECT: {s.google_cloud_project!r} (set for BigQuery / GDELT) | {bq}"
    )
    typer.echo("Wikipedia pageviews: no key required")


@app.command()
def wiki(
    project: str = typer.Argument("en.wikipedia", help="e.g. en.wikipedia, hr.wikipedia"),
    title: str = typer.Argument("Polarization", help="Article title (spaces ok)"),
    days: int = typer.Option(30, help="How many days back from today (ignored if --start/--end set)"),
    start: Optional[str] = typer.Option(
        None,
        "--start",
        help="Start date YYYY-MM-DD (use with --end for a fixed historical window)",
    ),
    end: Optional[str] = typer.Option(
        None,
        "--end",
        help="End date YYYY-MM-DD (inclusive in API; use with --start)",
    ),
) -> None:
    """Fetch daily pageviews and save JSON under data/raw/."""
    if (start or end) and not (start and end):
        raise typer.BadParameter("Use both --start and --end, or neither.")
    if start and end:
        d_start = date.fromisoformat(start)
        d_end = date.fromisoformat(end)
    else:
        d_end = date.today()
        d_start = d_end - timedelta(days=days)
    path = wikipedia.save_pageviews_json(project, title, d_start, d_end)
    typer.echo(f"Wrote {path}")


@app.command("sketch-ping")
def sketch_ping(
    corp: Optional[str] = typer.Option(
        None,
        "--corp",
        help="Corpus id (e.g. preloaded/hrwac). Default: SKETCH_DEFAULT_CORP in .env",
    ),
) -> None:
    """Call Sketch Engine corp_info; saves JSON under data/raw/ (tests user + API key)."""
    path = sketchengine.save_corp_info(corpname=corp)
    typer.echo(f"Wrote {path}")


@app.command("sketch-view")
def sketch_view(
    cql: str = typer.Option(
        'q[word="Hrvatska"]',
        "--cql",
        help='Full CQL (must start with q[). Default: q[word="Hrvatska"] in hrWaC.',
    ),
    corp: str = typer.Option(
        sketchengine.CROATIAN_WEB_CORPUS_DEFAULT,
        "--corp",
        help="Croatian web corpus in Sketch (default: preloaded/hrwac22_rft1 — current hrWaC 2.2+).",
    ),
    pagesize: int = typer.Option(5, help="Lines per request (keep small; FUP applies)."),
) -> None:
    """
    **Concordance (view)** on a corpus — run a CQL and save JSON under data/raw/.

    Auth: ``SKETCH_ENGINE_USER`` and ``SKETCH_ENGINE_KEY`` in .env. Default corpus is
    the latest **hrWaC** web crawl on Sketch Engine (``preloaded/hrwac22_rft1`` from the
    public corpus page *open in Sketch Engine* link).
    """
    path = sketchengine.save_concordance_sample(cql, corpname=corp, pagesize=pagesize)
    typer.echo(f"Wrote {path}")


@app.command("sketch-slurs")
def sketch_slurs(
    config: Path = typer.Option(
        batch_sketch.DEFAULT_CONFIG,
        "--config",
        exists=True,
        help="Path to slurs_terms.json (Croatian terms use hrWac by default).",
    ),
    corp: Optional[str] = typer.Option(
        None,
        "--corp",
        help="Sketch corpus id (default: preloaded/hrwac22_rft1).",
    ),
    pagesize: int = typer.Option(3, help="KWIC lines per term; keep small (FUP)."),
    lang: str = typer.Option(
        "hrv",
        "--lang",
        help="Which config entries to run: hrv | eng | all",
    ),
    dry_run: bool = typer.Option(False, help="List CQL only; no API calls."),
) -> None:
    """
    For each slur in config: **word-form** CQL on **hrWac 2.2+**; writes
    ``data/processed/sketch_hrwac_slurs.json`` (and a timestamped copy).
    """
    if lang not in ("hrv", "eng", "all"):
        raise typer.BadParameter("Use --lang hrv, eng, or all")
    out = batch_sketch.run_hrwac_slurs(
        config,
        corpname=corp,
        pagesize=pagesize,
        lang_filter=lang,
        dry_run=dry_run,
    )
    typer.echo(f"Wrote {out}")
    if not dry_run:
        typer.echo("Next: python -m pipeline refresh-output  # merge into presentation_report.md")


@app.command()
def er_sample(
    keyword: str = typer.Argument("political polarization", help="Search keyword"),
    lang: str = typer.Option("eng", help="Language code (e.g. eng, hrv)"),
) -> None:
    """Test Event Registry and save a small JSON sample (requires API key)."""
    path = eventregistry.save_sample(keyword=keyword, lang=lang)
    typer.echo(f"Wrote {path}")


@app.command("er-evidence")
def er_evidence(
    keyword: str = typer.Argument(
        ...,
        help="Search keyword or short phrase (see keywordSearchMode in Event Registry docs)",
    ),
    lang: str = typer.Option("hrv", help="lang code: eng, hrv, deu, ..."),
    count: int = typer.Option(30, help="Max articles (API cap 100)"),
    window_days: int = typer.Option(
        31,
        help="Recency: articles in last N days (forceMaxDataTimeWindow). Ignored if --date-start set.",
    ),
    date_start: Optional[str] = typer.Option(
        None,
        help="Optional YYYY-MM-DD (requires archive; may return 0 on some plans).",
    ),
    date_end: Optional[str] = typer.Option(None, help="Optional YYYY-MM-DD end (use with --date-start)."),
    mode: str = typer.Option(
        "phrase",
        help="keywordSearchMode: phrase | simple | exact (Event Registry).",
    ),
    loc: str = typer.Option("body", help="keywordLoc: body | title | title,body"),
    no_csv: bool = typer.Option(False, help="Only write JSON, not CSV table."),
) -> None:
    """
    Pull news evidence: full JSON + CSV table (title, url, date, source, excerpt).

    See https://www.newsapi.ai/documentation/examples and Event Registry *Searching for articles* wiki.
    """
    if (date_start or date_end) and not (date_start and date_end):
        raise typer.BadParameter("Use both --date-start and --date-end, or neither.")

    jpath, cpath = eventregistry.save_evidence(
        keyword,
        lang=lang,
        count=count,
        csv_also=not no_csv,
        force_max_data_time_window=window_days,
        date_start=date_start,
        date_end=date_end,
        keyword_search_mode=mode,
        keyword_loc=loc,
    )
    typer.echo(f"Wrote {jpath}")
    if cpath:
        typer.echo(f"Wrote {cpath}")


@app.command("er-batch")
def er_batch(
    config: Path = typer.Option(
        batch_eventregistry.DEFAULT_CONFIG,
        "--config",
        help="Path to slurs_terms.json (see config/ in the repo).",
        exists=True,
    ),
    dry_run: bool = typer.Option(False, help="List queries from config; no API calls."),
    no_summary: bool = typer.Option(False, help="Skip writing data/processed/eventregistry_summary.csv"),
) -> None:
    """
    Run all Event Registry queries in config (throttled); writes JSON+CSV per id
    and a batch log under data/raw/.
    """
    path = batch_eventregistry.run_batch(
        config_path=config,
        dry_run=dry_run,
        summarize_after=not no_summary,
    )
    if dry_run:
        typer.echo("Dry run (no API calls).")
    typer.echo(f"Batch log: {path}")
    if not no_summary and not dry_run:
        s = __import__("pipeline.config", fromlist=["get_settings"]).get_settings()
        typer.echo(f"Summary: {s.data_processed / 'eventregistry_summary.csv'}")


@app.command("er-summarize")
def er_summarize() -> None:
    """Re-scan data/raw/eventregistry_evidence_*.json and write data/processed/eventregistry_summary.csv."""
    p = summarize.write_summary_csv()
    typer.echo(f"Wrote {p}")


@app.command("run-all")
def run_all(
    skip_batch: bool = typer.Option(
        False,
        help="Do not call the API; only re-build data/processed/eventregistry_summary.csv from existing JSON.",
    ),
) -> None:
    """
    Default: run ``er-batch`` (all terms in config/slurs_terms.json) then you have
    ``data/processed/eventregistry_summary.csv``. Use --skip-batch if raw JSON is already there.
    """
    if not skip_batch:
        logp = batch_eventregistry.run_batch(summarize_after=True)
        typer.echo(f"Batch log: {logp}")
    else:
        p = summarize.write_summary_csv()
        typer.echo(f"Summary only: {p}")
    typer.echo("Optional: set dates in config/anchor_events.json for timeline figures.")


@app.command("run-free")
def run_free(
    skip_trends: bool = typer.Option(
        False,
        help="Skip Google Trends (still need: pip install -e '.[trends]').",
    ),
    skip_wiki: bool = typer.Option(False, help="Skip Wikipedia pageviews batch."),
) -> None:
    """
    **No Event Registry.** Free layers only: Wikipedia pageviews (config/wiki_pageviews.json) +
    Google Trends (config/trends_event_windows.json). For corpus work use Sketch in the browser/API separately.

    Event Registry *free* tier: see README — limited (e.g. ~30d archive, token cap). This command never calls ER.
    """
    s = get_settings()
    manifest: dict = {"date": date.today().isoformat(), "wikipedia": [], "trends": [], "ok": True}
    if not skip_wiki:
        for p in wiki_batch.run_wiki_batch():
            manifest["wikipedia"].append(str(p))
            typer.echo(f"Wrote {p}")
    if not skip_trends:
        try:
            from pipeline.ingest import google_trends

            for p in google_trends.run_from_config():
                manifest["trends"].append(str(p))
                typer.echo(f"Wrote {p}")
        except RuntimeError as e:
            manifest["trends_error"] = str(e)
            manifest["ok"] = False
            typer.echo(f"Trends: {e}")
    out = s.data_processed / f"free_pipeline_{date.today().isoformat()}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    typer.echo(f"Manifest: {out}")


@app.command("refresh-output")
def refresh_output_cmd() -> None:
    """
    Rebuild `output/presentation_metrics.csv`, `trends_spike_summary.csv`,
    `eventregistry_snapshot.csv`, and `output/presentation_report.md` from the latest
    `data/processed/*.json` and `data/raw/wiki_batch_*.json` (run `run-free` and `er-summarize` first).
    """
    for p in refresh_output.refresh_output_dir():
        typer.echo(f"Wrote {p}")


@app.command("trends-window")
def trends_window(
    center: str = typer.Argument(
        ...,
        help="Anchor day YYYY-MM-DD (e.g. event day; used for spike ratio in JSON summary).",
    ),
    pad: int = typer.Option(
        14,
        help="Days before and after center (inclusive window: [center-pad, center+pad]).",
    ),
    geo: str = typer.Option("US", help="Trends geo, e.g. US, HR"),
    keywords: str = typer.Option(
        "MAGA,Capitol riot,January 6th",
        help="Comma-separated search terms, max 5.",
    ),
    run_id: str = typer.Option(
        "custom_window",
        help="Filename stem under data/processed/trends_*",
    ),
) -> None:
    """
    Google Trends for a **date range around one day** (needs: pip install -e ".[trends]").

    Example: US Capitol — ``python -m pipeline trends-window 2021-01-06 --pad 21 --geo US``
    """
    from pipeline.ingest import google_trends

    c = date.fromisoformat(center)
    start = c - timedelta(days=pad)
    end = c + timedelta(days=pad)
    kws = [x.strip() for x in keywords.split(",") if x.strip()][:5]
    paths = google_trends.run_custom_window(
        run_id=run_id,
        label=f"window around {center} ±{pad}d",
        start=start,
        end=end,
        geo=geo,
        event_date=center,
        keywords=kws,
    )
    for p in paths:
        typer.echo(f"Wrote {p}")


@app.command("trends-run")
def trends_run(
    run_id: Optional[str] = typer.Option(
        None,
        "--id",
        help="Single run id from config/trends_event_windows.json (default: all runs).",
    ),
    config: Path = typer.Option(
        Path(__file__).resolve().parent.parent / "config" / "trends_event_windows.json",
        "--config",
        exists=True,
        help="JSON with runs[] (timeframe, geo, keywords, event_date).",
    ),
) -> None:
    """
    Google Trends (pytrends): relative interest 0-100 vs time for up to 5 keywords per run.

    Install: pip install -e ".[trends]". Not official; use as illustration next to Event Registry.
    """
    from pipeline.ingest import google_trends

    paths = google_trends.run_from_config(path=config, run_id=run_id)
    for p in paths:
        typer.echo(f"Wrote {p}")




@app.command("gdelt-snapshot")
def gdelt_snapshot(
    config: Path = typer.Option(
        Path(__file__).resolve().parent.parent / "config" / "gdelt_queries.json",
        "--config",
        exists=True,
        help="config/gdelt_queries.json: tables, date windows, theme substrings per run",
    ),
) -> None:
    """
    **GDELT GKG** row counts in BigQuery (V2Themes substring OR). Needs ``pip install -e '.[gdelt]'``,
    ``GOOGLE_CLOUD_PROJECT`` and service-account JSON or ADC. Writes ``data/processed/gdelt_summary_*.json``.
    """
    from pipeline.ingest import gdelt

    try:
        p = gdelt.run_gdelt_snapshot(config_path=config)
    except (RuntimeError, OSError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Wrote {p}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
