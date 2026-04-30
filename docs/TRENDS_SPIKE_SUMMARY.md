# `output/trends_spike_summary.csv` — data dictionary

**Source file in repo:** [trends_spike_summary.csv](https://github.com/bperak/slurs/blob/main/output/trends_spike_summary.csv)  
**How it is built:** `python -m pipeline refresh-output` merges spike blocks from `data/processed/trends_summary_<run_id>.json` (those JSON files are written by `python -m pipeline trends-run`). Implementation: `pipeline/ingest/google_trends.py` (`add_event_ratio`) and `pipeline/refresh_output.py` (`build_trends_spike_rows`, `_label_type`).

---

## What this table is

A **tabular summary of one heuristic on Google Trends**: for each configured **Trends run** (e.g. Oluja 2024, Capitol 2021, Thompson, Split folklore, Kirk, «Ujedinjeni protiv fašizma», …) and for each **keyword** in that run, the table stores how much **relative interest around a calendar anchor (`event_date`)** exceeds a **baseline** from the rest of the same time series in that run.

---

## Column definitions

| Column | Meaning |
|--------|---------|
| **`run_id`** | Window id from `config/trends_event_windows.json` (e.g. `hr_oluja_window_2024`, `us_capitol_contested_2021`). One row group = one Trends request with up to five keywords in the same geo and date span. |
| **`geo`** | Trends region for the request (e.g. `HR`, `US`). Values are **relative within that request**, not absolute search volume. |
| **`event_date`** | Calendar anchor day for the spike (e.g. `2025-11-30`). |
| **`window_days`** | Half-width of the event band: days **`[event_date − W, event_date + W]`** (default **`W = 3`**, i.e. ±3 days). |
| **`keyword`** | Exact keyword string in that run (same as in config / payload). |
| **`max_around_event`** | **Maximum** Trends value (0–100 in that request) **inside** the event window (all dates falling in `[event_date − window_days, event_date + window_days]`). |
| **`mean_outside`** | **Mean** of values **outside** that window (all other dates in the same series). If the mean would be **&lt; 0.1**, the code sets it to **0.1** to avoid division by near-zero and extreme ratios—so the baseline is not always a “pure” arithmetic mean in edge cases. |
| **`ratio`** | **`max_around_event / mean_outside`** (rounded in the JSON). **Interpretation:** “how many times the peak around the event exceeds typical level outside the window” **only for that run and keyword set**. **Not comparable** across two different Trends builds (different geo, span, or co-listed keywords rescale the 0–100 series—the JSON `caveat` states that 0–100 is relative within one request). |
| **`label_type`** | **Coarse tag for slides / sorting**, assigned in code (`_label_type`): e.g. `slur`, `slur_adjacent`, `contested_framing`, `commemoration`, `place`, `generic`, `broad`, `other`. This is **not** a Google classification; it is a small rule table over `run_id` + keyword text. Some keywords (e.g. `prosvjed` on `hr_*` runs) match an earlier branch before run-specific rules—treat `label_type` as a **convenience label**, not a ground-truth ontology. |

---

## How to read example rows

- A **large `ratio`** on a “public” label (e.g. *Oluja*, *Thompson*, *Charlie Kirk*, *prosvjed* in the antifascist window) means: in **that** window and **with those co-listed terms in the same request**, the index around the anchor has a **clearer peak** than the baseline outside ±3 days.
- **`ratio` 0 or very small** often means **no usable signal** in Trends for that context (e.g. flat or zero series around the event), not necessarily that the concept is unused in society.
- The **same keyword in different `run_id`s** is not the same experiment—**do not merge rows blindly** into one “popularity” ranking.

---

## Limitations (important for citations)

1. **Google Trends is not official statistics**—the project uses it as an **illustration** alongside Event Registry, corpus counts, etc.  
2. **0–100 is relative within one request** (see `caveat` in each `trends_summary_*.json`).  
3. **`ratio` is a simple heuristic** (max in ±W days vs. mean outside), not a controlled model.  
4. **`label_type` is a helper tag** for repository materials, not a scientific taxonomy.

---

## Related commands and files

- Regenerate summaries: `python -m pipeline trends-run` then `python -m pipeline refresh-output`.  
- Per-run time series: `data/processed/trends_iot_<run_id>.csv`.  
- Broader pipeline: [`PIPELINE.md`](PIPELINE.md).
