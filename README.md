# Slurs, polarization, and public discourse — empirical materials

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Repository:** [github.com/bperak/slurs](https://github.com/bperak/slurs)

- **Radna kopija na serveru:** kod koji se ovdje razvija nalazi se na VPS-u **Liks** u direktoriju **`~/slurs_cer_julija`** (apsolutno: `/home/Liks/slurs_cer_julija`).

This repository supports **comparative empirical work** on how **political slurs** and **polarizing labels** appear across **different kinds of evidence**: written **web text** (Croatian), **news indexes**, and **proxies for public attention** (Wikipedia traffic, Google Trends). It is built for **joint social–linguistic research** (e.g. STAL-style projects on Croatia and transatlantic comparators), not for scoring individuals or platforms.

---

## Research motivation

Political slurs do more than insult: they help **define who counts** as a legitimate participant in conflict. Empirically, no single archive gives a “true” frequency of slur use in society. Instead, this project **triangulates**:

1. **Linguistic usage in a large reference corpus** — token-level queries in **hrWac** (Croatian web text) via Sketch Engine, to see how often **selected surface forms** occur in **written** discourse under one tagging regime.

2. **News indexing** — article-level hits in **Event Registry** (and optionally coarse **GDELT GKG** rows in BigQuery) for short query strings, to contrast **editorial / wire** visibility with corpus counts.

3. **Attention proxies** — **Wikipedia** pageviews for chosen articles and **Google Trends** curves around **anchor dates** (e.g. commemorations, contested episodes), to relate **public salience** of labels to corpus and news measures.

The **scientific interest** lies in **tension between instruments**: the same string may be **rare in Trends**, **moderate in hrWac**, and **high or low in a news index** depending on language, window, and archive design. That **mismatch** is informative; it is not treated as noise to average away.

---

## What you will find here

| Artefact | Audience |
|----------|----------|
| **`output/presentation_report.md`** | **Primary handout**: hypotheses, anchor events, numeric snapshot, **Mermaid** design diagrams, limitations, and (§9) reproducibility notes. Regenerated from local data. |
| **`output/presentation_metrics.csv`**, **`trends_spike_summary.csv`**, **`eventregistry_snapshot.csv`** | Tables for slides or secondary analysis. |
| **`output/methodology_diagrams.md`** | Static methodology sketches. |
| **`config/*.json`** | Editable **keywords**, **event windows**, **anchor list**, and optional **GDELT** query definitions — version with your paper. |
| **`sources/`** | Project prose sources (e.g. proposal text); **not** required to run code. |

**Coding, installation, API keys, and CLI commands** are documented in **[`docs/PIPELINE.md`](docs/PIPELINE.md)** so this README stays oriented to **research questions and interpretation**.

---

## Ethics and use

- Queries involve **sensitive lexical items**. Use only for **peer-reviewed research, thesis work, or supervised teaching**, with **ethical review** where your institution requires it.
- Do **not** use outputs to **target, harass, or deanonymize** people. Concordance snippets are **illustrative**; handle them like any other **hate-adjacent** primary material.
- Respect **provider terms**, **Sketch Engine fair use**, and **rate limits**. Trends and similar tools are **not official** census data.

---

## What we do *not* claim

- **No causal identification** of events on slur rates from these layers alone.
- **No equation** of Trends scores with “search volume”, **Wikipedia** hits with “all readers”, or **Event Registry** counts with “all news”.
- **Corpus N** is a **concordance size** for a **token form** in **hrWac**, not moral prevalence and not spoken-language frequency.

Details and caveats are spelled out in **`output/presentation_report.md`** (§1.2, §7).

---

## Reproducing or extending the study

1. Clone the repository and follow **[`docs/PIPELINE.md`](docs/PIPELINE.md)** for environment setup and commands.
2. Copy **`.env.example`** to **`.env`** and add only the API access you need (corpus-only work is possible without news keys).
3. Edit **`config/`** to match your **terms**, **languages**, **event dates**, and **Trends windows**.
4. Run the pipeline steps in **`docs/PIPELINE.md`**, then **`refresh-output`** to rebuild **`output/presentation_report.md`**.

If you only need the **logic and limitations** without re-running APIs, read **`output/presentation_report.md`** as shipped (numbers may be snapshot-specific).

---

## Citation and license

- **License:** [MIT](LICENSE) — Copyright (c) 2026 Benedikt Perak.
- **Suggested citation (adapt to your style):**  
  *Perak, B. (2026). Slurs — empirical pipeline (corpus, news, attention) [Computer software]. GitHub. https://github.com/bperak/slurs*

For co-authored papers, cite the **paper** when available and mention this repository as **supplementary materials**.

---

## Further reading in-repo

- **[`docs/PIPELINE.md`](docs/PIPELINE.md)** — Installation, `.env`, CLI, file layout, security.  
- **[`output/presentation_report.md`](output/presentation_report.md)** — Full narrative, tables, diagrams, and procedural appendix.  
- **[`output/HANDOFF_execute_without_bigquery.md`](output/HANDOFF_execute_without_bigquery.md)** — Scope when skipping BigQuery/GDELT.
