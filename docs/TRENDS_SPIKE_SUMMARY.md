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

## Qualitative reading of the quantitative results

The numbers in this CSV are **not** a direct picture of “how much society hates or loves something.” They are a **compressed trace of relative search-like behaviour** in one commercial index, around dates you already treat as **politically salient** from news and chronology. The qualitative layer is: **what story about public attention is compatible with these shapes**, without turning the index into a moral thermometer.

### What a “spike” can mean (substantively)

When **`ratio` is high** for a keyword such as a **place**, **commemoration**, **person name**, or a **generic protest word** (*prosvjed*) in a run anchored on a real march or incident, a defensible qualitative gloss is:

- **Calendar clustering:** many people (or a smaller number of intense repeat queries—Trends does not distinguish) **oriented their curiosity** toward that label **in the same few days** as media coverage and offline mobilisation. The curve **bunches** around the episode rather than staying flat across the month.
- **Lexical anchoring:** the **exact string** you plotted is the one that temporarily **“carried”** the episode in search behaviour—often the **headline word** (city, artist, operation name) rather than a fine-grained legal or academic vocabulary.
- **Co-listing effects:** because up to five keywords are **normalized together inside one Trends request**, a spike can partly reflect **contrast** with flat lines for other terms in the same batch. Qualitatively: “this label dominated *this* bundle of queries in that window,” not “this label dominated the nation’s entire cognitive life.”

When **`ratio` is near zero** or **`max_around_event`** is very low for a string that is **politically loaded in discourse** (e.g. some slurs, or long movement names), the qualitative reading is usually **instrument sensitivity**, not “nothing happened in culture”:

- **Rare or taboo surface forms** may not be typed into Google at scale, or may be **filtered / bucketed** differently than mainstream labels.
- **Diacritics, spacing, and synonyms** matter: users search *Thompson*, *Split*, *prosvjed*; they rarely search a **full official march title** as a single exact phrase—so a flat line can mean **lexical mismatch**, not lack of protest.
- **News and street activity can spike without Trends** following the same phrase, especially for local or short-lived events.

### Juxtaposition the table is designed to support (H1 in plain language)

The **research-relevant contrast** is often **within the same row block** (`run_id`): **public names and places** show **visible bumps** around anchors, while **slur strings or slur-adjacent political insults** often stay **flat or at floor**. Qualitatively, that supports a careful claim:

- **Salience is unevenly “legible” to this instrument:** mainstream **event vocabulary** is what Trends is good at registering as a **relative** wave; **stigmatised or niche written forms** are systematically **under-read** here even when other evidence (corpus, news, ethnography) shows they matter in talk or text.

That is an argument about **where polarisation “shows up” in a search proxy**, not about who is “more polarised.”

### How to say it in a paper or talk (example formulations)

You can adapt sentences like these (always cite the method limits in the same breath):

- “Around [anchor date], **event-level labels** in our Trends window show a **concentrated uptick** relative to the rest of the month; **slur strings plotted in the same technical setup** do **not** reproduce that bump—consistent with **index blind spots** for certain lexical forms, not with a claim that slurs were absent from public life.”
- “We treat Google Trends as a **rough attention proxy**: it tracks **how a few chosen strings behave relative to each other** in one regional slice, not absolute prevalence of attitudes or hate.”
- “A **high `ratio` on *prosvjed*** near a coordinated march day suggests **generic protest vocabulary** briefly **aligned with media cycles**; it does **not** identify who searched or why.”

### Pairing numbers with qualitative sources

For a **thick** interpretation, combine this CSV with:

- **News text and headlines** (e.g. Event Registry exports in the same repo)—what **nouns** did editors repeat?
- **Corpus tokens** (hrWac / Sketch)—what **written** forms actually circulate?
- **Chronologies and reports** (anchors in `config/anchor_events.json`)—what **actually happened** on the ground?

Then the qualitative sentence becomes: **the same week**, **different instruments** highlight **different surfaces of the same episode**—and Trends is only one of those surfaces.

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
