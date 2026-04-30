# Handoff: proceed **without** BigQuery / GDELT

This note was added because **Cursor plan mode** could not modify non-markdown files. To apply the full change, either **switch to Agent mode** and ask to “execute the HANDOFF” or **copy the blocks below** into the repo manually.

## What was requested

- Implement the operational validation plan **skipping** Google BigQuery and GDELT for now.
- Use anchor events: **Thompson / Hipodrom Zagreb — 2025-07-05**; **Charlie Kirk (US) — 2025-09-10**.
- Extend the **presentation report** with **H1–H3** operational framing and **cross-source** notes (Wikipedia + Event Registry + Google Trends only).

## Files to create or replace

### 1. `config/anchor_events.json`

Replace contents with:

```json
{
  "version": 1,
  "source": "sources/STAL 2026/prijedlog.md",
  "description": "Time anchors for visual alignment with slur / news spikes. For Google Trends see config/trends_event_windows.json.",
  "croatia": [
    {
      "id": "thompson_hipodrom_2025",
      "label": "Koncert Marka Perkovića Thompsona (Hipodrom, Zagreb)",
      "location": "Hipodrom Zagreb",
      "approx_date": "2025-07-05"
    },
    {
      "id": "folklore_attack",
      "label": "Napad na srpske folkloraše",
      "approx_date": null
    },
    {
      "id": "antifascist_protest",
      "label": "Prosvjed protiv fašizma",
      "approx_date": null
    }
  ],
  "united_states": [
    {
      "id": "kirk_assassination_2025",
      "label": "Atentat / ubojstvo Charliea Kirka (SAD)",
      "location": "Utah Valley University, Orem, UT",
      "approx_date": "2025-09-10"
    },
    {
      "id": "capitol",
      "label": "Napad na Kapitol",
      "approx_date": "2021-01-06"
    }
  ]
}
```

### 2. `config/trends_event_windows.json`

In the `runs` array, **after** the `hr_oluja_window_2024` object (before the closing `]`), add a comma and the two new runs below (or merge by hand so JSON stays valid).

```json
    ,
    {
      "id": "hr_thompson_hipodrom_2025",
      "label": "HR: window around Thompson concert (Hipodrom Zagreb, 5 July 2025) — label salience (trends illustrative; may be sparse)",
      "timeframe": "2025-06-10 2025-07-25",
      "geo": "HR",
      "event_date": "2025-07-05",
      "keywords": ["Thompson", "Hipodrom", "Zagreb", "koncert", "Croatia"]
    },
    {
      "id": "us_kirk_2025",
      "label": "US: window around Charlie Kirk (Sept 2025) — name / movement salience (Trends 0–100, not news volume)",
      "timeframe": "2025-08-20 2025-09-25",
      "geo": "US",
      "event_date": "2025-09-10",
      "keywords": ["Charlie Kirk", "MAGA", "assassination", "Turning Point", "Trump"]
    }
```

### 3. `pipeline/refresh_output.py`

- Add `_format_anchor_bullets(config_dir: Path) -> str` reading `anchor_events.json` and returning markdown list items.
- Expand `_report_markdown(...)` with:
  - **Section “Anchor events”** (insert after the one-sentence pitch).
  - **Section “Operational hypotheses (no BigQuery in this export)”** with **H1** (Trends vs slurs), **H2** (deferred: news-scale check via GDELT when creds exist), **H3** (ER vs Trends index sensitivity), and a line stating **BigQuery/GDELT is not run** in this pipeline version.
- Renumber following sections (Suggested slide order, Key numbers, …) if you add two new H2-level sections.
- Update slide table row 10: mention **Sketch** + “optional **GDELT/BigQuery** later”; anchors in `config/anchor_events.json` are **filled** for Thompson and Kirk.

### 4. `output/methodology_diagrams.md`

Append a short **§6** that **GDELT on BigQuery** is an optional later layer; current stack = Wiki + Trends + Event Registry.

## Commands (after files are in place)

```bash
cd slurs_cer_julija && source .venv/bin/activate
pip install -e ".[trends]"   # if needed
python -m pipeline trends-run    # fetches all runs including 2025 windows (may fail on rate limits)
python -m pipeline run-free      # Wikipedia + Trends from config
python -m pipeline er-summarize
python -m pipeline refresh-output
```

**Note:** pytrends / Google may rate-limit or return empty series for some 2025 windows; the pipeline should still **document** the attempt in `data/processed/` and the report.

## BigQuery

**Not used** in this handoff. When you add credentials later, implement `pipeline/ingest/gdelt.py` and `gdelt-snapshot` per the Cursor plan file `operational_web_validation_cb567377.plan.md`.
