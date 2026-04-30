"""
Optional HTTP API to trigger ingests (local or server).

  cd slurs_cer_julija
  uvicorn pipeline.api_app:app --reload --port 8765

Protect with firewall / auth before exposing to the internet.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI, HTTPException

from pipeline import __version__
from pipeline.config import get_settings
from pipeline.ingest import eventregistry, wikipedia

app = FastAPI(title="Slurs pipeline API", version=__version__)


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "version": __version__,
        "eventregistry": s.has_eventregistry,
        "data_dir": str(s.pipeline_data_dir),
    }


@app.get("/ingest/wikipedia")
def ingest_wikipedia(
    project: str = "en.wikipedia",
    title: str = "Polarization",
    days: int = 30,
) -> dict:
    end = date.today()
    start = end - timedelta(days=days)
    try:
        path = wikipedia.save_pageviews_json(project, title, start, end)
    except Exception as e:  # noqa: BLE001 — surface to client
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"path": str(path)}


@app.get("/ingest/eventregistry-sample")
def ingest_er(keyword: str = "test", lang: str = "eng") -> dict:
    try:
        path = eventregistry.save_sample(keyword=keyword, lang=lang)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"path": str(path)}
