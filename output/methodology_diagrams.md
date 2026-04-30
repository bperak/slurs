# Methodology diagrams

These **Mermaid** blocks render in GitHub, many Markdown viewers, and IDEs. They mirror the **triangulation** design: corpus (primary) plus **auxiliary** news index and attention layers.

---

## 1. Triangulation of evidence

Three layers answer different questions; they are **not** expected to “agree” on the same number—interpretation is partly about **tension** between them.

```mermaid
flowchart TB
  subgraph L["Linguistic core (planned)"]
    S["Sketch Engine / hrWac"]
    S --> C["Concordance, collocations, embeddings"]
  end
  subgraph N["News index (optional)"]
    ER["Event Registry API"]
    ER --> H["Hit counts + article samples"]
  end
  subgraph A["Public attention (no key)"]
    W["Wikipedia pageviews"]
    T["Google Trends 0–100"]
  end
  L --- X["Contested events & labels"]
  N --- X
  A --- X
```

---

## 2. Data flow (from config to `output/`)

```mermaid
flowchart LR
  subgraph cfg["Config"]
    A1["anchor_events.json"]
    A2["wiki_pageviews.json"]
    A3["trends_event_windows.json"]
    A4["slurs_terms.json"]
  end
  subgraph run["Pipeline commands"]
    R1["run-free"]
    R2["er-batch / er-summarize"]
    R3["refresh-output"]
  end
  subgraph data["data/"]
    D1["raw/ *.json, *.csv"]
    D2["processed/ summaries, Trends CSV+JSON"]
  end
  subgraph out["output/"]
    O1["presentation_report.md"]
    O2["*.csv metrics"]
  end
  A2 --> R1
  A3 --> R1
  A4 --> R2
  R1 --> D1
  R1 --> D2
  R2 --> D1
  R2 --> D2
  D2 --> R3
  R3 --> O1
  R3 --> O2
```

---

## 3. “Spike ratio” around an anchor day (Google Trends)

Heuristic used in `trends_summary_*.json`: for each keyword, **max** interest in a **±N day** window around the event day vs **mean** interest **outside** that window. Ratio highlights **relative** salience, not absolute search volume.

```mermaid
flowchart TB
  E[Event date e.g. 2021-01-06] --> W[Window ±3 days]
  W --> M1["max(interest in window)"]
  O[All other days in series] --> M2["mean(interest outside window)"]
  M1 --> R["ratio = max / mean_outside"]
  M2 --> R
  R --> C["Caveat: 0–100 is within-query only; slurs often 0"]
```

---

## 4. Limitations at a glance

```mermaid
flowchart LR
  T["Trends"] --> T1["Relative; not official statistics"]
  T --> T2["Slurs often censored or too rare → 0"]
  ER2["Event Registry"] --> E1["Plan & window limit archive"]
  ER2 --> E2["Keyword phrasing changes hit counts"]
  W2["Wikipedia"] --> W1["Article choice ≠ slur use"]
  X["No causal claims"] --- T
  X --- ER2
  X --- W2
```

---

## 5. How this relates to the paper

- **Primary** linguistic analysis is still **corpus**-driven (hrWac); this repository’s export mainly **contextualises** slurs and labels with **attention** and **news index** snapshots.
- **Contested events** (same episode, different public names) are the **bridge** between layers: e.g. riot vs. protest language (US) or commemoration windows (HR).

Regenerate numbers: `python -m pipeline run-free` and `python -m pipeline refresh-output`.

---

## 6. BigQuery / GDELT (optional, not in default stack)

**GDELT** via **Google BigQuery** would add a large **news-scale** check next to Event Registry and Google Trends. It is **not** required for the current export: this project runs on **Wikipedia pageviews**, **Google Trends**, and **Event Registry** (optional) without cloud credentials.

When you add a GCP project and service-account JSON (typical on a VPS), you can plug in queries against the public `gdelt-bq` datasets and merge summaries into `output/` the same way as other `data/processed/*.json` sources. See `output/HANDOFF_execute_without_bigquery.md` and the operational validation plan for scope.
