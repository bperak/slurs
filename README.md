# Slurs — empirical pipeline (corpus, news, attention)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Repository:** [https://github.com/bperak/slurs](https://github.com/bperak/slurs)

Python toolkit for **triangulating** evidence on political slurs and polarization: **Sketch Engine / hrWac** (Croatian web corpus), **Event Registry** (news index), **Wikipedia** pageviews, **Google Trends** (illustrative), optional **GDELT GKG** via BigQuery. Outputs include **`output/presentation_report.md`** (talk handout with diagrams and procedures) and CSV summaries under **`output/`**.

> **Ethics:** This code queries **sensitive lexical items** in public archives. Use for **research and teaching** with institutional safeguards; do not use outputs to harass individuals. Respect each provider’s **terms**, **FUP** (Sketch), and **rate limits**.

---

## Quick start

```bash
git clone https://github.com/bperak/slurs.git
cd slurs
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # if present; otherwise create .env (see below)
python -m pipeline doctor
pytest -q
```

Optional extras:

```bash
pip install -e ".[trends]"   # Google Trends (pytrends)
pip install -e ".[gdelt]"   # BigQuery / GDELT (google-cloud-bigquery)
```

Regenerate the **presentation handout** after ingests:

```bash
python -m pipeline run-free
python -m pipeline er-batch          # needs EVENTREGISTRY_API_KEY
python -m pipeline er-summarize
python -m pipeline trends-run
python -m pipeline sketch-slurs      # needs SKETCH_ENGINE_* for hrWac N
python -m pipeline refresh-output
```

Full command reference and file paths are documented inside **`output/presentation_report.md`** (sections **§8–§9**) after you run `refresh-output` once.

---

## Environment variables (`.env`)

| Variable | Used for |
|----------|----------|
| `EVENTREGISTRY_API_KEY` | Event Registry / [newsapi.ai](https://newsapi.ai/) |
| `SKETCH_ENGINE_USER`, `SKETCH_ENGINE_KEY` | [Sketch Engine](https://www.sketchengine.eu/documentation/api-documentation/) HTTP API |
| `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS` | Optional **GDELT** BigQuery jobs |
| `YOUTUBE_DATA_API_KEY`, `OPENAI_API_KEY` | Optional future / local experiments |

Never commit `.env`. **`data/`** is listed in `.gitignore** (local pulls and keys stay off GitHub by default).

---

## Finish a credible stack *without* Event Registry

You can still build a useful empirical picture:

1. **Sketch / hrWac** — main **Croatian** token frequencies (`sketch-slurs`, `sketch-view`).
2. **Wikipedia** — `run-free` / `wiki` + `config/wiki_pageviews.json` (**no key**).
3. **Google Trends** — `pip install -e ".[trends]"` then `run-free` or `trends-run` (**unofficial**; slurs often **0**).
4. **Anchors** — `config/anchor_events.json` for figure alignment.
5. **GDELT** (optional) — `gdelt-snapshot` with GCP project + auth.

Event Registry free tier is **limited** ([plans](https://eventregistry.org/plans)); use **`er-batch`** for targeted pulls or skip.

---

## Recommended tools (priority)

| Priority | Tool | API key? | Role |
|----------|------|----------|------|
| 1 | **Wikimedia pageviews** | No | Attention proxy (EN/HR articles) |
| 2 | **Event Registry** | Yes | News search / excerpts |
| 3 | **BigQuery + GDELT** | GCP | Global GKG-scale checks |
| 4 | **Sketch (hrWac)** | Yes | **hrWaC 2.2+** default: `preloaded/hrwac22_rft1` |
| 5 | **YouTube Data API** | Yes | Optional video layer |
| 6 | **OpenAI** | Yes | Optional — only on **your** exported text |

---

## API keys (short links)

- **Event Registry:** [newsapi.ai](https://newsapi.ai/) → dashboard → `EVENTREGISTRY_API_KEY` in `.env`. Docs: [search articles](https://newsapi.ai/documentation?tab=searchArticles).
- **Google Cloud:** [console](https://console.cloud.google.com/) → BigQuery / YouTube as needed → `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, `YOUTUBE_DATA_API_KEY`.
- **Sketch:** [app.sketchengine.eu](https://app.sketchengine.eu/) → My account → API key → `SKETCH_ENGINE_USER`, `SKETCH_ENGINE_KEY`.

---

## Commands (cheat sheet)

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

---

## Optional local HTTP API

```bash
uvicorn pipeline.api_app:app --reload --port 8765
# GET http://127.0.0.1:8765/health
```

Do not expose without authentication.

---

## Data layout (local)

| Path | Content |
|------|---------|
| `config/slurs_terms.json` | Keywords for `er-batch` / Sketch HRV batch |
| `config/anchor_events.json` | Event anchors for slides |
| `config/wiki_pageviews.json` | Wikipedia batch for `run-free` |
| `config/trends_event_windows.json` | Trends runs |
| `config/gdelt_queries.json` | Optional GDELT windows |
| `data/raw/` | Evidence JSON, wiki batches (gitignored) |
| `data/processed/` | Summaries, Trends CSV, `sketch_hrwac_slurs.json`, manifests (gitignored) |
| `output/` | `presentation_report.md`, `presentation_metrics.csv`, etc. |

---

## Tests

```bash
pytest -q
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Benedikt Perak.

---

## Security

- Never commit **`.env`** or raw **API responses** with personal data.
- Rotate keys exposed in chat or CI logs.
- Use provider **key restrictions** where available.
