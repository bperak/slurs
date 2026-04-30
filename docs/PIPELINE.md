# Pipeline — installation, configuration, and CLI

Technical reference for developers and reproducibility. For **research framing, hypotheses, and how to read results**, start with the root [**README.md**](../README.md) and **`output/presentation_report.md`** (especially §1–§7 and §9).

---

## Requirements

- Python **3.9+**
- Virtual environment recommended

```bash
git clone https://github.com/bperak/slurs.git
cd slurs
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # then edit (see table below)
python -m pipeline doctor
pytest -q
```

### Optional extras

```bash
pip install -e ".[trends]"   # Google Trends (pytrends; unofficial)
pip install -e ".[gdelt]"   # BigQuery / GDELT (google-cloud-bigquery)
```

---

## Environment variables (`.env`)

| Variable | Used for |
|----------|----------|
| `EVENTREGISTRY_API_KEY` | [Event Registry / newsapi.ai](https://newsapi.ai/) |
| `SKETCH_ENGINE_USER`, `SKETCH_ENGINE_KEY` | [Sketch Engine HTTP API](https://www.sketchengine.eu/documentation/api-documentation/) |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS` | Optional **GDELT** BigQuery |
| `YOUTUBE_DATA_API_KEY`, `OPENAI_API_KEY` | Optional experiments |

Never commit `.env`. The repo **`.gitignore`** excludes `data/` (local pulls and large artefacts).

### Where to obtain keys

- **Event Registry:** [newsapi.ai](https://newsapi.ai/) → dashboard → API key. Docs: [search articles](https://newsapi.ai/documentation?tab=searchArticles).
- **Google Cloud:** [console](https://console.cloud.google.com/) → enable BigQuery / YouTube as needed.
- **Sketch:** [app.sketchengine.eu](https://app.sketchengine.eu/) → My account → Generate API key.

---

## Typical refresh sequence

After changing config or credentials, rebuild processed data then the handout:

```bash
python -m pipeline run-free
python -m pipeline er-batch          # requires EVENTREGISTRY_API_KEY
python -m pipeline er-summarize
python -m pipeline trends-run
python -m pipeline sketch-slurs      # requires SKETCH_ENGINE_* for hrWac counts
# optional: pip install -e ".[gdelt]"  # once
python -m pipeline gdelt-snapshot    # requires GOOGLE_CLOUD_PROJECT + auth
python -m pipeline refresh-output
```

See **`output/presentation_report.md` §8–§9** for narrative + diagrams of the same flow.

---

## CLI cheat sheet

```bash
python -m pipeline doctor

python -m pipeline wiki hr.wikipedia "Hrvatska" --days 90
python -m pipeline er-sample "polarization" --lang eng
python -m pipeline er-evidence "political polarization" --lang eng --count 30

python -m pipeline sketch-ping --corp "preloaded/hrwac22_rft1"
python -m pipeline sketch-view --cql 'q[word="Hrvatska"]' --pagesize 5
python -m pipeline sketch-slurs

python -m pipeline er-batch
python -m pipeline run-free
python -m pipeline run-all
python -m pipeline er-summarize

python -m pipeline trends-run
python -m pipeline trends-run --id us_capitol_contested_2021

python -m pipeline gdelt-snapshot
python -m pipeline refresh-output
```

Use `--help` on any subcommand for Typer options.

---

## Repository layout (technical)

| Path | Role |
|------|------|
| `pipeline/` | Python package: ingest, CLI, `refresh_output` |
| `config/slurs_terms.json` | Keywords for Event Registry batch and Sketch HRV batch |
| `config/anchor_events.json` | Event dates / labels for alignment |
| `config/wiki_pageviews.json` | Wikipedia pages for `run-free` |
| `config/trends_event_windows.json` | Trends runs (geo, dates, keyword batches) |
| `config/gdelt_queries.json` | GDELT BigQuery windows and theme filters |
| `config/sketch_croatian.json` | Default hrWac corpus id note |
| `data/raw/` | Raw API JSON, wiki batches (gitignored) |
| `data/processed/` | Summaries, CSV series, manifests (gitignored) |
| `output/` | Regenerated `presentation_report.md`, CSV tables |
| `tests/` | `pytest` |

---

## Optional local HTTP API

```bash
uvicorn pipeline.api_app:app --reload --port 8765
# GET http://127.0.0.1:8765/health
```

Do not expose to the public internet without authentication.

---

## Security

- Do not commit **`.env`** or exports containing personal data from news bodies.
- Rotate any key that leaked into chat or CI logs.
- Use provider key restrictions when available.
