# Getting data around specific days (event windows)

Use this when you have an **anchor date** (e.g. from `config/anchor_events.json` or your fieldwork) and want **data in a range** around it.

| Source | What you get | Command / config | Limits |
|--------|----------------|------------------|--------|
| **Wikipedia pageviews** | Daily views for one article in `[start, end]` | `python -m pipeline wiki en.wikipedia "Political polarization" --start 2021-01-01 --end 2021-01-31` | **No API key**; [WMF API](https://wikimedia.org/api/rest_v1/) has a lower bound (roughly 2015+ for most wikis). |
| **Google Trends** | Relative 0–100 interest per **batch** of ≤5 terms | `python -m pipeline trends-window 2021-01-06 --pad 14 --geo US --keywords "MAGA,Capitol riot,January 6th"` | Needs `pip install -e ".[trends]"` — **unofficial**; slurs often **0**; use as illustration. |
| **Event Registry (news)** | Article hits in a **calendar** range | `python -m pipeline er-evidence "MAGA" --lang eng --date-start 2021-01-01 --date-end 2021-01-31` | Needs key; **free plans** may only return **recent** window or **0** for deep archive — check [newsapi.ai](https://newsapi.ai/) dashboard. |
| **Sketch / hrWac** | Concordance, frequency in **corpus** (not by calendar day in this repo) | Sketch Engine UI or API | Your subscription; time metadata depends on corpus design. |
| **GDELT (optional)** | News/event tables in BigQuery | `pipeline/ingest/gdelt.py` placeholder + BigQuery | Google Cloud; SQL by date. |

## Quick examples

**1. Wikipedia: one month around a known US event (Capitol, Jan 2021)**  
```bash
python -m pipeline wiki en.wikipedia "Political polarization" \
  --start 2020-12-15 --end 2021-02-15
```

**2. Google Trends: ±3 weeks around Jan 6, 2021 (US)**  
```bash
python -m pipeline trends-window 2021-01-06 --pad 21 --geo US \
  --keywords "MAGA,libtard,Capitol riot,Stop the Steal,January 6th" \
  --run-id capitol_2021_pm21d
```

**3. Event Registry: same calendar slice (if your plan returns rows)**  
```bash
python -m pipeline er-evidence "Ustaše" --lang hrv --count 50 \
  --date-start 2024-08-01 --date-end 2024-08-10
```

**4. Still “last N days from today” (no fixed history)**  
```bash
python -m pipeline wiki hr.wikipedia "Hrvatska" --days 30
```

## Filling in Croatian anchors

Edit `config/anchor_events.json` with `approx_date` (YYYY-MM-DD) for Thompson / folklorists / protest, then use those dates in `--start` / `--end` and `trends-window` with `--geo HR` and HR-relevant keywords.

---

*Outputs land in `data/raw/` (Wikipedia, Event Registry) and `data/processed/` (Trends).*
