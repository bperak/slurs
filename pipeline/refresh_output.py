"""Regenerate `output/presentation_*.csv` and `output/presentation_report.md` from `data/`."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.config import get_settings


def _wiki_sum_max(path: Path) -> tuple[int, int, int]:
    d = json.loads(path.read_text(encoding="utf-8"))
    items = d.get("items") or []
    views = [int(x["views"]) for x in items if isinstance(x, dict) and "views" in x]
    if not views:
        return 0, 0, 0
    return len(views), sum(views), max(views)


def _latest_free_manifest(processed: Path) -> dict[str, Any] | None:
    cands = sorted(processed.glob("free_pipeline_*.json"), reverse=True)
    if not cands:
        return None
    return json.loads(cands[0].read_text(encoding="utf-8"))


def _wiki_paths_from_manifest(
    m: dict[str, Any] | None, data_raw: Path, config_dir: Path
) -> list[tuple[str, Path, str, str]]:
    """
    Returns list of (id, path, project_label, title_label).
    """
    cfg = json.loads((config_dir / "wiki_pageviews.json").read_text(encoding="utf-8"))
    id_to_meta: dict[str, tuple[str, str]] = {}
    for p in cfg.get("pages", []):
        pid = (p.get("id") or "").strip()
        if pid:
            id_to_meta[pid] = (p.get("project", ""), p.get("title", ""))

    out: list[tuple[str, Path, str, str]] = []
    if m and m.get("wikipedia"):
        for s in m["wikipedia"]:
            p = Path(s)
            m2 = re.search(r"wiki_batch_([^.]+)\.json$", p.name)
            if not m2:
                continue
            wid = m2.group(1)
            proj, title = id_to_meta.get(wid, ("", wid))
            out.append((wid, p, proj, title))
    else:
        for p in sorted(data_raw.glob("wiki_batch_*.json")):
            m2 = re.search(r"wiki_batch_([^.]+)\.json$", p.name)
            if m2:
                wid = m2.group(1)
                proj, title = id_to_meta.get(wid, ("", wid))
                out.append((wid, p, proj, title))
    return out


def _label_type(keyword: str, run_id: str) -> str:
    k = keyword.lower()
    if run_id.startswith("us_"):
        if k in ("capitol riot", "january 6th", "stop the steal"):
            return "contested_framing"
        if k == "maga":
            return "slur_adjacent"
        if k == "libtard":
            return "slur"
    if run_id.startswith("hr_"):
        if k == "oluja":
            return "commemoration"
        if "usta" in k:
            return "slur"
        if k in ("hrvatska", "prosvjed", "izbori"):
            return "broad" if k == "hrvatska" else "generic"
        if "thompson" in run_id or "hipodrom" in run_id:
            return "commemoration" if k in ("thompson", "koncert", "hipodrom", "zagreb") else "broad"
    if run_id.startswith("us_") and "kirk" in run_id:
        if k in ("charlie kirk", "maga", "trump", "turning point"):
            return "contested_framing" if k != "maga" else "slur_adjacent"
        if k == "assassination":
            return "contested_framing"
    return "other"


def build_trends_spike_rows(s: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rid = s["run"]["id"]
    geo = s["run"]["geo"]
    ed = s["run"]["event_date"]
    spike = s.get("spike") or {}
    wdays = spike.get("window_days", 3)
    for kw, stats in (spike.get("by_keyword") or {}).items():
        rows.append(
            {
                "run_id": rid,
                "geo": geo,
                "event_date": ed,
                "window_days": wdays,
                "keyword": kw,
                "max_around_event": stats.get("max_around_event"),
                "mean_outside": stats.get("mean_outside"),
                "ratio": stats.get("ratio"),
                "label_type": _label_type(kw, rid),
            }
        )
    return rows


def _latest_gdelt_summary_path(processed: Path) -> Path | None:
    cands = sorted(processed.glob("gdelt_summary_*.json"), reverse=True)
    return cands[0] if cands else None


def _gdelt_presentation(
    data_processed: Path,
) -> tuple[str, list[dict[str, Any]]]:
    """H2 one-paragraph blurb + optional rows for presentation_metrics."""
    p = _latest_gdelt_summary_path(data_processed)
    pm_rows: list[dict[str, Any]] = []
    if not p or not p.is_file():
        return (
            "Not in this run. Install the optional BigQuery extra (see docs/PIPELINE.md), set "
            "GOOGLE_CLOUD_PROJECT and auth, then: python -m pipeline gdelt-snapshot.",
            [],
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    blurb: list[str] = [f"File `data/processed/{p.name}` (project {data.get('project', '')})."]
    for r in data.get("runs") or []:
        rid = r.get("id", "")
        n = r.get("gkg_record_count_theme_match")
        err = r.get("err") or r.get("error")
        w0 = r.get("partition_start", "")
        w1 = r.get("partition_end", "")
        b = r.get("total_bytes_processed")
        if err:
            short = str(err)[:240].replace("\n", " ")
            blurb.append(f"**{rid}:** BigQuery error ({short})")
        elif n is not None:
            bb = f" ~{b // 1_000_000}M bytes billed" if isinstance(b, int) and b else ""
            blurb.append(
                f"**{rid}:** **{n:,}** GKG rows where V2Themes matches any token ({w0}–{w1}).{bb}"
            )
        pm_rows.append(
            {
                "section": "GDELT GKG (BigQuery)",
                "metric": f"{rid} — GKG row count (V2Themes substring OR)",
                "value": n if n is not None and not err else "",
                "unit": "rows" if n is not None and not err else "error" if err else "",
                "source_file": f"data/processed/{p.name}",
                "notes": (str(err)[:200] if err else f"window {w0}..{w1}"),
            }
        )
    return " ".join(blurb), pm_rows


def _load_sketch_hrwac(data_processed: Path) -> dict[str, Any] | None:
    p = data_processed / "sketch_hrwac_slurs.json"
    if not p.is_file():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return d if isinstance(d, dict) else None


def _linguistic_pitch_fragment_from_sketch(d: dict[str, Any] | None) -> str:
    if not d or not d.get("items"):
        return "**linguistic** evidence (hrWac / Sketch — planned as core)"
    ok_any = any(
        isinstance(it, dict) and it.get("ok") and it.get("concsize") is not None
        for it in d["items"]
    )
    if ok_any:
        return (
            "**measured** **word-form** **concordance sizes** in **hrWac** 2.2+ (Sketch, §2.5)"
        )
    return "**linguistic** evidence (hrWac / Sketch — planned or pending credentials; see §2.5)"


def _format_sketch_hrwac_block(d: dict[str, Any] | None) -> str:
    if not d:
        return (
            "*(Not generated.) Set `SKETCH_ENGINE_USER` and `SKETCH_ENGINE_KEY` in `.env`, then run* "
            "`python -m pipeline sketch-slurs` *— small `pagesize` and throttling respect Sketch FUP.*\n"
        )
    if not d.get("items") and d.get("note") and "SKETCH" in (d.get("note") or ""):
        return (
            f"*{d['note']} Run `python -m pipeline sketch-slurs` when credentials are available.*\n"
        )
    lines = [
        "| id | Keyword | N (≈ concordance size) | Notes |",
        "|----|---------|--------------------------|-------|",
    ]
    corp = d.get("corpname", "")
    for it in d.get("items") or []:
        if not isinstance(it, dict):
            continue
        qid = (it.get("id") or "").replace("|", " ")
        kw = (it.get("keyword") or "").replace("|", " ")
        if it.get("dry_run"):
            n = "—"
        elif it.get("ok") and it.get("concsize") is not None:
            c = it["concsize"]
            if isinstance(c, (int, float)) and c == int(c):
                c = int(c)
            n = f"{c:,}" if isinstance(c, int) else str(c)
        else:
            err = (it.get("error") or "—")[:120]
            n = f"Error: {err}" if it.get("error") else "—"
        if not it.get("ok") and it.get("error"):
            no = (str(it.get("error")) or "")[:100]
        else:
            no = (it.get("note") or "").replace("|", "/")[:80] if it.get("note") else ""
        lines.append(f"| {qid} | {kw} | {n} | {no} |")
    rel = f"`data/processed/sketch_hrwac_slurs.json`"
    lines.append("")
    lines.append(
        f"Corpus: `{corp}`; **CQL** is surface **word** form, not lemma; FUP: batched in pipeline with a small `pagesize`. "
        f"Source: {rel}."
    )
    return "\n".join(lines) + "\n"


def _sketch_limitation_bullet(d: dict[str, Any] | None) -> str:
    if d and any(
        isinstance(it, dict) and it.get("ok") and it.get("concsize") is not None
        for it in d.get("items") or []
    ):
        return (
            "- **hrWac / Sketch** — **N** in §2.5 is a **word-form** concordance size in the tagged **web** corpus, not a claim about spoken usage. **FUP** limits batch sampling. Trends and Event Registry remain **auxiliary** **attention** / **news** indices."
        )
    return (
        "- **hrWac / Sketch** = primary **linguistic** ground; run `sketch-slurs` to add **N** in §2.5. Until then this export leans on **Wikipedia** / **Trends** / **ER** for convenience."
    )


def _sketch_key_number_bullet(d: dict[str, Any] | None) -> str:
    if not d or not d.get("items"):
        return (
            "*(No hrWac slur batch in `data/processed/` yet — run* `python -m pipeline sketch-slurs` *.)*"
        )
    bits: list[str] = []
    for it in d.get("items") or []:
        if not isinstance(it, dict) or not it.get("ok"):
            continue
        c = it.get("concsize")
        if c is None:
            continue
        try:
            ci = int(c)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        kw = (it.get("keyword") or "").strip() or (it.get("id") or "")
        bits.append(f"*{kw}* **{ci:,}**")
    if not bits:
        return "*(hrWac file present but no successful N); check §2.5 and credentials.*"
    return (
        f"**hrWac 2.2+ (word-form CQL; not lemma):** " + "; ".join(bits) + " — *see* `data/processed/sketch_hrwac_slurs.json`"
    )


def _sketch_pm_from_json(d: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not d or not d.get("items"):
        return rows
    for it in d.get("items") or []:
        if not isinstance(it, dict) or it.get("dry_run"):
            continue
        c = it.get("concsize")
        rows.append(
            {
                "section": "Sketch Engine (hrWac 2.2+)",
                "metric": f"{(it.get('id') or '')} — {it.get('keyword', '')!s} (word CQL) — concordance size N",
                "value": c if c is not None and it.get("ok") else "",
                "unit": "hits (approx. index)" if c is not None and it.get("ok") else "error" if it.get("error") else "",
                "source_file": "data/processed/sketch_hrwac_slurs.json",
                "notes": (it.get("error") or (it.get("note") or ""))[:200],
            }
        )
    return rows


def refresh_output_dir(
    out_dir: Path | None = None,
    *,
    data_processed: Path | None = None,
    data_raw: Path | None = None,
) -> list[Path]:
    s = get_settings()
    data_processed = data_processed or s.data_processed
    data_raw = data_raw or s.data_raw
    project_root = s.pipeline_data_dir.parent
    out_dir = out_dir or project_root / "output"
    config_dir = project_root / "config"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    manifest = _latest_free_manifest(data_processed)
    wiki_list = _wiki_paths_from_manifest(manifest, data_raw, config_dir)

    pm_rows: list[dict[str, Any]] = []
    for wid, wpath, proj, title in wiki_list:
        if not wpath.is_file():
            continue
        n_days, sm, mx = _wiki_sum_max(wpath)
        rel = wpath.resolve().as_posix().split("/slurs_cer_julija/")[-1]
        if "data/" not in rel:
            rel = f"data/raw/{wpath.name}"
        base = f"{title} ({proj})" if title else wid
        pm_rows.extend(
            [
                {
                    "section": "Wikipedia",
                    "metric": f"{base} — sum daily views ({n_days}d window)",
                    "value": sm,
                    "unit": "views sum",
                    "source_file": rel,
                    "notes": "Public attention proxy; not slur-specific"
                    if "polariz" in (title or "").lower() or "hr" in (proj or "")
                    else "",
                },
                {
                    "section": "Wikipedia",
                    "metric": f"{base} — peak single-day views",
                    "value": mx,
                    "unit": "views max",
                    "source_file": rel,
                    "notes": "Peak in source JSON items",
                },
            ]
        )

    def _er_metric_label(stem: str) -> str:
        rest = stem.removeprefix("eventregistry_evidence_")
        if rest.startswith("eng_"):
            w = rest[4:].replace("_", " ")
            if w == "maga":
                w = "MAGA"
            return f"ENG {w} — total matching articles (index)"
        if rest.startswith("hrv_"):
            raw = rest[4:]
            if raw == "ustase":
                return "HRV Ustaše — total"
            w = raw.replace("_", " ")
            return f"HRV {w} — total"
        if "polarization" in rest.lower():
            return "EN political polarization (probe query) — total"
        return f"Event Registry {rest[:80]} — total"

    def _er_note(stem: str) -> str:
        sl = stem.lower()
        if "maga" in sl:
            return "High base rate in news"
        if "teabagger" in sl:
            return "Often zero — sparse or phrasing"
        if "polarization" in sl:
            return "Separate probe not same as slur list"
        return ""

    er_path = data_processed / "eventregistry_summary.csv"
    if er_path.is_file():
        er = pd.read_csv(er_path, encoding="utf-8")
        for _, r in er.iterrows():
            stem = str(r.get("stem", ""))
            tr = r.get("total_results")
            pm_rows.append(
                {
                    "section": "Event Registry",
                    "metric": _er_metric_label(stem),
                    "value": tr if tr == tr else "",
                    "unit": "hits",
                    "source_file": "data/processed/eventregistry_summary.csv",
                    "notes": _er_note(stem),
                }
            )

    trend_jsons = sorted(data_processed.glob("trends_summary_*.json"))
    if manifest and manifest.get("trends"):
        want = {Path(p).name for p in manifest["trends"] if "trends_summary" in p}
        if want:
            trend_jsons = [p for p in trend_jsons if p.name in want]
    else:
        trend_jsons = [p for p in trend_jsons if "demo" not in p.name.lower()]
    ts_rows: list[dict[str, Any]] = []
    for tpath in trend_jsons:
        sj = json.loads(tpath.read_text(encoding="utf-8"))
        wdays = (sj.get("spike") or {}).get("window_days", 3)
        sp = (sj.get("spike") or {}).get("by_keyword") or {}
        rel = f"data/processed/{tpath.name}"
        for kw, stats in sp.items():
            ratio = stats.get("ratio")
            note = "0–100 relative index; not absolute volume"
            if ratio in (0, 0.0) and "lib" in kw.lower():
                note = "Suppressed or too rare in Trends for this window"
            pm_rows.append(
                {
                    "section": "Google Trends",
                    "metric": f"{tpath.stem} — {kw} spike vs baseline (±{wdays}d)",
                    "value": ratio if ratio is not None else "",
                    "unit": "ratio",
                    "source_file": rel,
                    "notes": note,
                }
            )
        ts_rows.extend(build_trends_spike_rows(sj))

    gdelt_h2_text, gdelt_pm = _gdelt_presentation(data_processed)
    pm_rows.extend(gdelt_pm)

    sketch_d = _load_sketch_hrwac(data_processed)
    pm_rows.extend(_sketch_pm_from_json(sketch_d or {}))

    pm_rows.append(
        {
            "section": "Methods",
            "metric": "Core linguistic evidence (hrWac 2.2+)",
            "value": "Sketch Engine" if sketch_d and (sketch_d.get("items") or []) else "see §2.5 / sketch-slurs",
            "unit": "—",
            "source_file": "data/processed/sketch_hrwac_slurs.json",
            "notes": "Word-form CQL; primary corpus in prijedlog.md",
        }
    )
    pm_rows.append(
        {
            "section": "Methods",
            "metric": "Event anchors for figures (editable)",
            "value": "config/anchor_events.json",
            "unit": "—",
            "source_file": "config/anchor_events.json",
            "notes": "Fill exact dates in paper",
        }
    )

    pm_df = pd.DataFrame(pm_rows)
    pm_out = out_dir / "presentation_metrics.csv"
    pm_df.to_csv(pm_out, index=False, encoding="utf-8")
    written.append(pm_out)

    if ts_rows:
        ts_df = pd.DataFrame(ts_rows)
        ts_out = out_dir / "trends_spike_summary.csv"
        ts_df.to_csv(ts_out, index=False, encoding="utf-8")
        written.append(ts_out)

    if er_path.is_file():
        er = pd.read_csv(er_path, encoding="utf-8")
        snap_rows = []
        for _, r in er.iterrows():
            stem = str(r.get("stem", ""))
            rest = stem.replace("eventregistry_evidence_", "", 1)
            if rest.startswith("eng_"):
                reg, term = "ENG", rest[4:].replace("_", " ")
            elif rest.startswith("hrv_"):
                reg, term = "HRV", rest[4:].replace("_", " ")
            else:
                reg, term = "?", rest
            if "political" in rest.lower():
                term = "polarization (probe)"
            # display diacritics
            if "ustase" in term.lower():
                term = "Ustaše"
            snap_rows.append(
                {
                    "file_stem": stem,
                    "total_results": r.get("total_results"),
                    "returned_in_page": r.get("returned_in_page"),
                    "lang_region": reg,
                    "search_term (from file id)": term,
                }
            )
        snap_out = out_dir / "eventregistry_snapshot.csv"
        pd.DataFrame(snap_rows).to_csv(snap_out, index=False, encoding="utf-8")
        written.append(snap_out)

    en_sum = en_peak = hr_sum = hr_peak = 0
    for wid, wpath, _proj, title in wiki_list:
        if not wpath.is_file():
            continue
        _n, sm, mx = _wiki_sum_max(wpath)
        tlow = (title or "").lower()
        if "polarization" in tlow:
            en_sum, en_peak = sm, mx
        elif "hrvatsk" in tlow or wid.startswith("hr"):
            hr_sum, hr_peak = sm, mx

    def _er_total(substr: str) -> int:
        if not er_path.is_file():
            return 0
        e = pd.read_csv(er_path, encoding="utf-8")
        row = e[e["stem"].str.contains(substr, case=False, na=False)]
        if row.empty:
            return 0
        v = row.iloc[0].get("total_results")
        return int(v) if v == v and v is not None else 0

    us_json = data_processed / "trends_summary_us_capitol_contested_2021.json"
    hr_json = data_processed / "trends_summary_hr_oluja_window_2024.json"
    cap_r = jan6 = maga_r = lib_r = st_s = 0.0
    if us_json.is_file():
        u = json.loads(us_json.read_text(encoding="utf-8"))
        sp = (u.get("spike") or {}).get("by_keyword") or {}
        cap_r = sp.get("Capitol riot", {}).get("ratio") or 0
        jan6 = sp.get("January 6th", {}).get("ratio") or 0
        maga_r = sp.get("MAGA", {}).get("ratio") or 0
        lib_r = sp.get("libtard", {}).get("ratio") or 0
        st_s = sp.get("Stop the Steal", {}).get("ratio") or 0
    ol_r = u_r = 0.0
    if hr_json.is_file():
        h = json.loads(hr_json.read_text(encoding="utf-8"))
        sp = (h.get("spike") or {}).get("by_keyword") or {}
        ol_r = sp.get("Oluja", {}).get("ratio") or 0
        u_r = sp.get("Ustaše", {}).get("ratio") or 0

    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_date = (manifest or {}).get("date") or date.today().isoformat()
    anchor_bullets = _format_anchor_events_bullets(config_dir / "anchor_events.json")
    pitch_linguistic = _linguistic_pitch_fragment_from_sketch(sketch_d)
    sketch_block = _format_sketch_hrwac_block(sketch_d)
    sk_bul = _sketch_key_number_bullet(sketch_d)
    sk_lim = _sketch_limitation_bullet(sketch_d)
    report = _report_markdown(
        anchor_bullets=anchor_bullets,
        gdelt_h2=gdelt_h2_text,
        en_sum=en_sum,
        en_peak=en_peak,
        hr_sum=hr_sum,
        hr_peak=hr_peak,
        maga_hits=_er_total("maga"),
        ustase_hits=_er_total("ustase"),
        cap_r=float(cap_r),
        jan6=float(jan6),
        maga_r=float(maga_r),
        lib_r=float(lib_r),
        st_s=float(st_s),
        ol_r=float(ol_r),
        usta_trend=float(u_r),
        gen_at=gen_at,
        free_manifest_date=run_date,
        pitch_linguistic_fragment=pitch_linguistic,
        sketch_corpus_table=sketch_block,
        sketch_key_numbers_bullet=sk_bul,
        sketch_limitation_bullet=sk_lim,
    )
    rep_path = out_dir / "presentation_report.md"
    rep_path.write_text(report, encoding="utf-8")
    written.append(rep_path)
    return written


def _presentation_mermaid_section() -> str:
    """
    Static Mermaid blocks for the presentation report (GitHub / VS Code / many slide tools).
    Kept free of f-string ``{`` braces so it can be concatenated safely.
    """
    return (
        "## 1.5 Diagrams (Mermaid)\n\n"
        "**What this subsection is for:** Each figure below is a **visual outline** you can paste into slides. "
        "Under every diagram you get a **caption** (what to say aloud) and an **explanation** (what the picture "
        "**means** for your argument). Technical command-line detail lives in **§9**.\n\n"
        "### A. Triangulation — three evidence families\n\n"
        "**Caption (say aloud):** “We do not rely on one archive. Linguistic **token** rates in hrWac, **news index** "
        "hits, and **attention** curves each measure something different; we read them **side by side**.”\n\n"
        "**Explanation:** The three coloured groups are **independent families** of evidence. **Corpus** counts "
        "tell you how common a **surface string** is in **written** Croatian web text. **News indices** tell you "
        "how often **article bodies** match a query in a **commercial** archive (with its own language and recency "
        "rules). **Attention** layers show **relative** public interest (Trends) or **traffic** to chosen Wikipedia "
        "pages—not slur frequency on those pages. Dotted lines from **Anchor events** mean: we **line up** charts "
        "and tables in **time** around the same calendar episodes; that is **alignment**, not a claim that the event "
        "**caused** the counts.\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  subgraph CORP[\"Corpus linguistic\"]\n"
        "    SK[\"Sketch Engine hrWac 2.2+\"]\n"
        "    N[\"Word-form CQL concordance N\"]\n"
        "    SK --> N\n"
        "  end\n"
        "  subgraph NEWS[\"News indices\"]\n"
        "    ER[\"Event Registry\"]\n"
        "    GD[\"GDELT GKG optional\"]\n"
        "  end\n"
        "  subgraph ATTN[\"Public attention\"]\n"
        "    WP[\"Wikipedia pageviews\"]\n"
        "    GT[\"Google Trends\"]\n"
        "  end\n"
        "  ANC[\"Anchor events config\"]\n"
        "  ANC -. temporal alignment .-> SK\n"
        "  ANC -. temporal alignment .-> ER\n"
        "  ANC -. temporal alignment .-> WP\n"
        "```\n\n"
        "### B. From configuration to this report\n\n"
        "**Caption (say aloud):** “Everything you see in the handout is **reproducible**: JSON configs drive CLI "
        "commands, raw pulls land under `data/raw`, summaries under `data/processed`, then one compiler pass writes "
        "`output/`.”\n\n"
        "**Explanation:** This is the **software path**, not the theory. **`refresh-output`** never calls external "
        "APIs; it only **reads** files already on disk. That separation matters: you can **rebuild the narrative** "
        "after fixing a query in config **without** re-hitting paid APIs, as long as the underlying JSON/CSV still "
        "exists.\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  CFG[\"Config JSON\"] --> CMD[\"CLI ingest\"]\n"
        "  CMD --> RAW[\"data/raw\"]\n"
        "  CMD --> PROC[\"data/processed\"]\n"
        "  RAW --> REF[\"refresh-output\"]\n"
        "  PROC --> REF\n"
        "  REF --> OUT[\"output tables and this MD\"]\n"
        "```\n\n"
        "### C. Operational hypotheses (H1–H3)\n\n"
        "**Caption (say aloud):** “We register three **testable** intuitions: Trends favours mainstream labels over "
        "slur strings; BigQuery GKG—when run—gives a coarse **global news** check; ER and Trends **rank** terms "
        "differently.”\n\n"
        "**Explanation:** **H1** is about **suppression and scale** in Google’s Trends product (zeros are common for "
        "slurs). **H2** is optional and depends on **GCP**; it is about **very large** news tables, not fine semantics. "
        "**H3** is a **methods** warning: comparing **rank orders** across ER and Trends is misleading without "
        "reading how each index is built.\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  H1[\"H1 Trends\"] --> D1[\"Public labels often beat slur strings\"]\n"
        "  H2[\"H2 GKG\"] --> D2[\"News-scale coarse theme counts\"]\n"
        "  H3[\"H3 Indices\"] --> D3[\"ER and Trends need not rank alike\"]\n"
        "```\n\n"
        "### D. Optional: contested labels vs one episode (illustrative)\n\n"
        "**Caption (say aloud):** “The **same day** can carry **rival public names** for one episode; Trends often "
        "makes that visible. Slur strings may stay flat even when political labels spike.”\n\n"
        "**Explanation:** This diagram is a **pedagogical** device for **Jan 6–style** or **memory-politics** cases: "
        "you plot several **keywords** with **legitimate** descriptive disagreement (riot vs. protest; competing "
        "ethnonational labels) and compare **spike ratios** from `trends_summary_*.json`. It does **not** say which "
        "label is morally correct; it shows **where measurable attention goes** in one proprietary index.\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  EV[\"Same calendar episode\"] --> L1[\"Label A e.g. Capitol riot\"]\n"
        "  EV --> L2[\"Label B e.g. January 6th\"]\n"
        "  EV --> L3[\"Slur or adjacent string often flat in Trends\"]\n"
        "  L1 --> CMP[\"Compare curves and spike ratios\"]\n"
        "  L2 --> CMP\n"
        "  L3 --> CMP\n"
        "```\n\n"
    )


def _presentation_process_guide_section() -> str:
    """
    Long-form procedural documentation + extra Mermaid for ``presentation_report.md`` §9.
    Inserted via variable into the outer f-string (inner text may contain ``{`` safely).
    """
    return (
        "## 9. Processes and procedures (detailed reference)\n\n"
        "**Relationship to §1–§7:** The sections above explain **findings and talk structure**. This appendix explains **machinery**: "
        "commands, config files, and on-disk paths so a colleague can **reproduce** the tables. If anything here seems to "
        "repeat an idea from §1–§7, treat **§9** as the **technical** spelling-out. A consolidated **install / CLI** sheet "
        "also lives in **`docs/PIPELINE.md`** at the repository root.\n\n"
        "This section explains **what each pipeline step does**, **what it reads and writes**, and **how to interpret** outputs. "
        "Executive diagrams also appear in **§1.5**. Commands assume the project root `slurs_cer_julija`, venv active, and "
        "optional keys in **`.env`** (the repo loads it via `python-dotenv`; you do not commit secrets).\n\n"
        "---\n\n"
        "### 9.1 Configuration map (inputs)\n\n"
        "| File | Role |\n"
        "|------|------|\n"
        "| `config/slurs_terms.json` | Keyword list for **Event Registry** batch and (HRV subset) **Sketch** word queries |\n"
        "| `config/wiki_pageviews.json` | Which Wikipedia articles and date span **`wiki`** uses |\n"
        "| `config/trends_event_windows.json` | **Google Trends** runs: geo, event date, keyword batches (≤5 per request) |\n"
        "| `config/anchor_events.json` | Human-readable **anchor events** for slides and alignment narrative |\n"
        "| `config/gdelt_queries.json` | Optional **BigQuery** windows and theme substrings for **GDELT** |\n"
        "| `config/sketch_croatian.json` | Notes + default **hrWac** corpus id for Sketch |\n"
        "| `docs/PIPELINE.md` | **Install, `.env`, CLI**, repository layout (developer reference) |\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  subgraph CFG[\"config\"]\n"
        "    A[\"slurs_terms.json\"]\n"
        "    B[\"wiki_pageviews.json\"]\n"
        "    C[\"trends_event_windows.json\"]\n"
        "    D[\"anchor_events.json\"]\n"
        "    E[\"gdelt_queries.json\"]\n"
        "  end\n"
        "  subgraph ENV[\"environment\"]\n"
        "    DOT[\".env API keys and paths\"]\n"
        "  end\n"
        "  CFG --> CLI[\"python -m pipeline …\"]\n"
        "  DOT --> CLI\n"
        "```\n\n"
        "---\n\n"
        "### 9.2 Procedure: `run-free` (no paid news APIs)\n\n"
        "**Purpose:** Refresh the **free** layers only: **Wikipedia** daily pageviews and **Google Trends** time series, "
        "and write a small **manifest** listing what was produced.\n\n"
        "**Reads:** `config/wiki_pageviews.json`, `config/trends_event_windows.json`. "
        "**Requires:** `pip install -e \".[trends]\"` for Trends (pytrends is unofficial; respect rate limits).\n\n"
        "**Writes:**\n"
        "- `data/raw/wiki_batch_<id>.json` — per-article daily views in the configured window.\n"
        "- `data/processed/trends_iot_<run_id>.csv` — 0–100 interest by date for each keyword batch.\n"
        "- `data/processed/trends_summary_<run_id>.json` — metadata plus **spike ratio** (max around event vs baseline).\n"
        "- `data/processed/free_pipeline_<date>.json` — manifest with paths for downstream **`refresh-output`**.\n\n"
        "**Procedure (internal):** For each Wikipedia page, call the Wikimedia pageviews API. "
        "For each Trends run in JSON, build a timeframe around `event_date`, request interest-over-time for up to five "
        "keywords per batch, sleep between runs on 429, compute spike statistics, save CSV + JSON.\n\n"
        "**Interpretation:** Wikipedia sums are **broad attention** to a chosen article, not slur frequency. "
        "Trends values are **relative within each request**, not absolute search volume; **slurs often read as zero**.\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  WCFG[\"wiki_pageviews.json\"] --> WB[\"wiki_batch run\"]\n"
        "  TCFG[\"trends_event_windows.json\"] --> TR[\"trends ingest\"]\n"
        "  WB --> RAW[\"data/raw\"]\n"
        "  TR --> PROC[\"data/processed\"]\n"
        "  RAW --> MAN[\"free_pipeline manifest\"]\n"
        "  PROC --> MAN\n"
        "```\n\n"
        "---\n\n"
        "### 9.3 Procedure: Event Registry (`er-batch`, `er-summarize`, single pulls)\n\n"
        "**Purpose:** Sample **indexed news** matching each keyword (phrase / simple / exact per API settings), "
        "with language and recency filters.\n\n"
        "**Credentials:** `EVENTREGISTRY_API_KEY` in `.env`. Free tiers are **window- and quota-limited**; "
        "zero hits often means **index or query mismatch**, not absence of discourse offline.\n\n"
        "**`er-batch` procedure:** Load `config/slurs_terms.json`, throttle with `sleep_seconds_between_requests`, "
        "for each row call the article search API, write `data/raw/eventregistry_evidence_<id>.json` (+ CSV when enabled), "
        "append to `data/raw/batch_run_<timestamp>.log.json`, optionally regenerate **`eventregistry_summary.csv`**.\n\n"
        "**`er-summarize` procedure:** Scan existing `eventregistry_evidence_*.json` files and rebuild "
        "`data/processed/eventregistry_summary.csv` (totals and pagination metadata) **without** new HTTP calls.\n\n"
        "**`er-evidence` / `er-sample`:** One-off probes for testing credentials or ad hoc keywords.\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  ST[\"slurs_terms.json\"] --> LOOP[\"For each query row\"]\n"
        "  LOOP --> API[\"Event Registry HTTP API\"]\n"
        "  API --> J[\"eventregistry_evidence JSON\"]\n"
        "  API --> C[\"optional CSV excerpts\"]\n"
        "  J --> SUM[\"er-summarize\"]\n"
        "  SUM --> CSV2[\"eventregistry_summary.csv\"]\n"
        "```\n\n"
        "---\n\n"
        "### 9.4 Procedure: Google Trends (`trends-run`, `trends-window`)\n\n"
        "**Purpose:** Plot **relative** public interest (0–100) for labelled keywords near anchor dates.\n\n"
        "**`trends-run`:** Same engine as inside `run-free`, but can be run alone after config edits. "
        "Reads `trends_event_windows.json`; optional `--id` limits to one run.\n\n"
        "**`trends-window`:** Ad hoc: pass center date, padding days, geo, and a comma-separated keyword list.\n\n"
        "**Outputs:** CSV time series + JSON summaries under `data/processed/`. **`refresh-output`** reads summaries "
        "to populate §5 spike bullets and `trends_spike_summary.csv`.\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  CFG2[\"trends_event_windows.json\"] --> PYT[\"pytrends client\"]\n"
        "  PYT --> IOT[\"trends_iot CSV\"]\n"
        "  PYT --> SUMT[\"trends_summary JSON\"]\n"
        "  SUMT --> REF2[\"refresh-output\"]\n"
        "```\n\n"
        "---\n\n"
        "### 9.5 Procedure: Sketch Engine / hrWac (`sketch-ping`, `sketch-view`, `sketch-slurs`)\n\n"
        "**Purpose:** **Linguistic** grounding on the large Croatian **web** corpus **hrWac 2.2+** "
        "(default corpus id `preloaded/hrwac22_rft1`).\n\n"
        "**Credentials:** `SKETCH_ENGINE_USER` and `SKETCH_ENGINE_KEY` (HTTP Basic to Bonito API).\n\n"
        "- **`sketch-ping`:** `corp_info` — validates user, key, and corpus name; writes JSON under `data/raw/`.\n"
        "- **`sketch-view`:** Single **concordance** (`view`) for a full **CQL** string starting with `q[`; "
        "synchronous mode, small `pagesize`.\n"
        "- **`sketch-slurs`:** For each **HRV** (or `eng` / `all` via `--lang`) entry in `slurs_terms.json`, "
        "builds `q[word=\"…\"]` (surface token, not lemma), calls `view`, records **`concsize`** and a few **KWIC** lines, "
        "throttles between calls (**FUP**). Writes `data/processed/sketch_hrwac_slurs.json` plus a timestamped copy.\n\n"
        "**Interpretation:** `concsize` is a **corpus index size** for that token form in hrWac, not usage in speech "
        "and not a moral frequency claim.\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "  participant CLI as Pipeline CLI\n"
        "  participant API as Sketch Bonito API\n"
        "  participant CORP as hrWac corpus\n"
        "  CLI->>API: GET view with CQL and corpname\n"
        "  API->>CORP: execute query\n"
        "  CORP-->>API: concsize plus Lines\n"
        "  API-->>CLI: JSON concordance\n"
        "  CLI->>CLI: write sketch_hrwac_slurs.json\n"
        "```\n\n"
        "---\n\n"
        "### 9.6 Procedure: GDELT GKG via BigQuery (`gdelt-snapshot`, optional)\n\n"
        "**Purpose:** Coarse **news-scale** check: count **GKG** rows in a partition window where **`V2Themes`** "
        "contains configured substrings (OR logic).\n\n"
        "**Requires:** `pip install -e \".[gdelt]\"`, **`GOOGLE_CLOUD_PROJECT`** in `.env`, and Application Default "
        "Credentials or **`GOOGLE_APPLICATION_CREDENTIALS`** to a service account JSON with BigQuery job scope.\n\n"
        "**Writes:** `data/processed/gdelt_summary_<date>.json`. **`refresh-output`** merges the latest file into "
        "**§3 H2** text and **`presentation_metrics.csv`** when present.\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  Q[\"config gdelt_queries.json\"] --> BQ[\"BigQuery job\"]\n"
        "  BQ --> T[\"gdelt-bq.gdeltv2.gkg_partitioned\"]\n"
        "  T --> OUTG[\"gdelt_summary JSON\"]\n"
        "  OUTG --> REFG[\"refresh-output\"]\n"
        "```\n\n"
        "---\n\n"
        "### 9.7 Procedure: `refresh-output` (report compiler)\n\n"
        "**Purpose:** Deterministic **regeneration** of `output/presentation_report.md`, "
        "`output/presentation_metrics.csv`, `output/trends_spike_summary.csv`, and `output/eventregistry_snapshot.csv` "
        "from whatever is already on disk under `data/`.\n\n"
        "**Does not** call Wikipedia, Trends, Event Registry, Sketch, or BigQuery. It **reads** latest manifests, "
        "summary JSON/CSV, Wikipedia batch JSON, optional `sketch_hrwac_slurs.json`, optional `gdelt_summary_*.json`, "
        "and fills the Markdown template (including **§1.5** and **§9** static annex, dynamic tables for §2.5, "
        "and numeric slots for §4–§5).\n\n"
        "**When to run:** After any ingest step you want reflected in the handout, e.g. the sequence in **§8**.\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  subgraph IN[\"inputs on disk\"]\n"
        "    M1[\"free_pipeline manifest\"]\n"
        "    M2[\"wiki_batch JSON\"]\n"
        "    M3[\"trends_summary JSON\"]\n"
        "    M4[\"eventregistry_summary.csv\"]\n"
        "    M5[\"sketch_hrwac_slurs.json\"]\n"
        "    M6[\"gdelt_summary optional\"]\n"
        "    M7[\"anchor_events.json\"]\n"
        "  end\n"
        "  IN --> R[\"refresh_output.py\"]\n"
        "  R --> MD[\"presentation_report.md\"]\n"
        "  R --> PM[\"presentation_metrics.csv\"]\n"
        "  R --> OT[\"other output CSV\"]\n"
        "```\n\n"
        "---\n\n"
        "### 9.8 Other helpful commands\n\n"
        "| Command | Use |\n"
        "|---------|-----|\n"
        "| `python -m pipeline doctor` | Print which **env vars** are set (no secret values) |\n"
        "| `python -m pipeline wiki …` | One article’s **pageviews** without editing `wiki_pageviews.json` |\n"
        "| `python -m pipeline run-all` | Convenience wrapper: **`er-batch`** then summary (same as manual ER chain) |\n"
        "| `python -m pipeline er-evidence …` | Single **Event Registry** pull with CLI flags for window and search mode |\n"
        "| `python -m pipeline trends-window …` | **Ad hoc** Trends window from the command line |\n\n"
        "---\n\n"
        "### 9.9 Diagram index in this document\n\n"
        "| Location | Diagrams |\n"
        "|----------|----------|\n"
        "| **§1.5** | Triangulation (A), config-to-report (B), hypotheses H1–H3 (C), contested labels (D) |\n"
        "| **§9** | Config map (9.1), `run-free` (9.2), Event Registry loop (9.3), Trends (9.4), Sketch sequence (9.5), "
        "GDELT (9.6), `refresh-output` (9.7) |\n\n"
        "For additional static methodology figures (outside this auto-generated file), see **`output/methodology_diagrams.md`**.\n\n"
    )


def _format_anchor_events_bullets(anchor_path: Path) -> str:
    if not anchor_path.is_file():
        return "- *(config/anchor_events.json not found)*\n"
    d = json.loads(anchor_path.read_text(encoding="utf-8"))
    lines: list[str] = []
    for key, title in (("croatia", "Croatia"), ("united_states", "United States")):
        for e in d.get(key) or []:
            eid = e.get("id", "")
            lab = e.get("label", "")
            ad = e.get("approx_date") or "—"
            loc = (e.get("location") or "").strip()
            extra = f" ({loc})" if loc else ""
            lines.append(f"- **{eid}** ({title}): {lab} — **{ad}**{extra}")
    return "\n".join(lines) if lines else "- *(no events in config)*\n"


def _report_markdown(
    *,
    anchor_bullets: str,
    gdelt_h2: str,
    en_sum: int,
    en_peak: int,
    hr_sum: int,
    hr_peak: int,
    maga_hits: int,
    ustase_hits: int,
    cap_r: float,
    jan6: float,
    maga_r: float,
    lib_r: float,
    st_s: float,
    ol_r: float,
    usta_trend: float,
    gen_at: str,
    free_manifest_date: str,
    pitch_linguistic_fragment: str = "**linguistic** evidence (hrWac / Sketch — planned as core)",
    sketch_corpus_table: str = "",
    sketch_key_numbers_bullet: str = "",
    sketch_limitation_bullet: str = (
        "- **hrWac / Sketch** = primary **linguistic** ground; run `sketch-slurs` to add **N** in §2.5."
    ),
) -> str:
    sk_t = (sketch_corpus_table or "").rstrip() or "*(Not generated; run* `sketch-slurs` *with Sketch credentials — see §2.5.)*"
    sk_b = (sketch_key_numbers_bullet or "").strip() or "*(Add hrWac: run* `sketch-slurs` *— see* `data/processed/sketch_hrwac_slurs.json` *.)*"
    mermaid_block = _presentation_mermaid_section()
    process_guide_block = _presentation_process_guide_section()
    return f"""# Slurs, polarization, and public discourse
**Empirical snapshot for STAL / joint work (Cerovac & Perhat)**
*Generated: {gen_at} — pipeline manifest date `{free_manifest_date}`. See `output/*.csv` and `data/processed/` for sources.*

---

## How to read this document (where the explanations are)

**Sections 1–7** are the **substantive handout**: they explain **what we measured**, **why it matters for slurs and polarization**, and **how not to over-read** the numbers. **§1.5** adds diagrams; **each diagram** now has a **caption** (what to say in the room) and an **explanation** (what the picture means). **§8** is only the **shell commands** to regenerate files. **§9** is a **technical appendix** (inputs, outputs, procedures). If you opened this file looking for **paragraphs about findings**, stay in **§1–§7**; if you looked at **§8–§9 only**, scroll up.

---

## 1. One-sentence pitch

Political slurs do not only harm targets: they **shape** who counts as a worthy interlocutor. This project **triangulates** (1) {pitch_linguistic_fragment}, (2) **news index** samples (Event Registry, where used), and (3) **public attention** (Wikipedia pageviews + Google Trends) around **contested** events and **competing labels**.

### 1.1 Plain-language gloss (what this project actually measures)

This repository **does not** output a single “polarization score” for society. Instead it **lines up several imperfect lenses**: **(a)** how often selected **surface word forms** appear in a large **Croatian web corpus** (Sketch / hrWac), **(b)** how many **news articles** match short textual queries in **Event Registry** (with language and recency filters), and **(c)** how **Wikipedia traffic** and **Google Trends** curves move near **dates you label as important** in `config/anchor_events.json`. The **scientific payoff** is **disagreement between lenses**: the same string can be **rare in Trends**, **non-trivial in hrWac**, and **high or low in ER** depending on phrasing and archive coverage—**that triangulation** is the finding, not any one column in isolation.

### 1.2 What we do *not* claim (scope guardrails)

We do **not** infer **causal** effects of an event on hate speech. We do **not** treat **Trends** as absolute search volume, **Wikipedia** as a proxy for “all readers”, or **Event Registry** as the whole news world. We do **not** treat **hrWac N** as moral frequency or as spoken-language prevalence. Every layer has **documented limits** (see **§7**).

---

{mermaid_block}
---

## 2. Anchor events (paper / talk; see `config/anchor_events.json`)

**Explanation:** Anchor events are **calendar and place anchors** for your **talk**, not statistical regressors inside this export. They give **shared reference dates** (e.g. Capitol 2021-01-06, Thompson concert 2025-07-05, Kirk 2025-09-10) so that **Trends windows**, **ER recency filters**, and **slide titles** point at the **same episode**. Rows with **“—”** dates are placeholders: fill `approx_date` in `config/anchor_events.json` when you lock the paper.

{anchor_bullets}

**Trends runs** for 2025 windows are listed in `config/trends_event_windows.json` (`hr_thompson_hipodrom_2025`, `us_kirk_2025`) — pull them with `python -m pipeline trends-run`. Google / pytrends may rate-limit or return empty series; optional **BigQuery** via `gdelt-snapshot` (see **`docs/PIPELINE.md`**).

---

## 2.5. Croatian web corpus (Sketch / hrWac 2.2+)

**Explanation:** This table is the **linguistic** leg of triangulation. **N** is Sketch’s **concordance size** for the exact **word token** in the query (e.g. the string as written in `config/slurs_terms.json`), **not** a lemma count and **not** sentiment. A **small N** means “this surface form is rare in **this** tagged web snapshot”, not “the concept is unused in politics”. A **large N** means “the token appears often in **this** corpus”, not “people approve of it”. The JSON file also stores a few **KWIC** lines for qualitative illustration—handle ethically in teaching.

{sk_t}

---

## 3. Operational hypotheses (falsifiable)

**Explanation:** Hypotheses here are **operational**: they refer to **measurable behaviour of our instruments**, not to deep causal laws of culture. **H1** is about **Trends’ numeric behaviour** around anchors versus slur strings. **H2** (when GDELT runs) is about **coarse GKG theme matches** in a BigQuery slice. **H3** is a **disciplining** claim: **do not** merge Event Registry and Trends into one ranking without reading **how** each is built.

- **H1 (attention / Trends):** Around anchor days, **public labels** (event names, places, movement names) tend to show **higher** relative 0–100 interest in Trends than many **slur** strings, which are often **0** or suppressed.
- **H2 (news at scale / GKG on BigQuery):** {gdelt_h2}
- **H3 (index sensitivity):** **Event Registry** hit counts and **Google Trends** curves are **not** the same design: do not expect them to **rank** terms identically (window, language, plan limits).

**How to falsify (examples):** For **H1**, find a stable window where a **slur string** repeatedly **outscores** mainstream labels around the same anchor (would weaken the illustrative pattern). For **H3**, show the **same** keyword list producing **opposite rank orders** in ER vs Trends **because of known filter differences**—that would **support** H3 as a methods fact, not refute the project.

**Cross-source stack:** **Wikipedia** (pageviews) + **Google Trends** + **Event Registry** (when `data/raw` has evidence) + **hrWac / Sketch** (`data/processed/sketch_hrwac_slurs.json` after `sketch-slurs`) + **optional GDELT** (`gdelt-snapshot` → `gdelt_summary_*.json`). Full table: `output/presentation_metrics.csv`.

---

## 4. Suggested slide order (8–12 slides)

**Explanation:** The table is a **storyboard**, not a rigid rule. Use it when moving from **methods** to **examples**: introduce triangulation (rows 1–3), show **terms** (row 4), then give **one number each** from Wikipedia, ER, Trends, and corpus where available (rows 5–7), then **contested framing** (rows 8–9), then **limitations** (row 10). **Row 3a** is where you show **hrWac N** as “written Croatian web, token form”.

| # | Slide title | Content |
|---|-------------|---------|
| 1 | Title | *Slurs and Political Polarization* — epistemic & political harms; Croatia & Anglo-American comparison |
| 2 | Research gap | Slurs in **equal-status** political conflict; not only hate speech law cases |
| 3 | Design | **Triangulation**: corpus (hrWac) + news (Event Registry) + attention (Wiki, Trends) + **anchor events** (`config/anchor_events.json`) |
| 3a | **hrWac (Sketch)** | **HRV** slur list: **word-form** CQL → **N** (concordance size) + small KWIC in `data/processed/sketch_hrwac_slurs.json` (also §2.5) — run `sketch-slurs` |
| 4 | Terms (prijedlog) | EN: libtard, MAGA, teabagger — HR: jugočetnici, jugokomunisti, klerofašist, Ustaše |
| 5 | **Wikipedia (attention, no key)** | EN *Political polarization* article: **~{en_sum/1000:.1f}k** total daily views over 90 days; peak day **{en_peak}** views. HR *Hrvatska*: **~{hr_sum/1000:.1f}k** sum; peak **{hr_peak}** — *broad* attention, not slur-specific* |
| 6 | **Event Registry (news, if available)** | **MAGA** & **Ustaše** return many index hits; several HR slur strings **rare or zero** in a short window — *phrase choice and archive limits matter* — see `output/eventregistry_snapshot.csv` |
| 7 | **Google Trends (illustration)** | **Jan 6 (2021)** & **Oluja (2024)** windows: mainstream labels **spike** more than some slur strings; *libtard* / *Ustaše* often **0** in Trends. **2025:** *Thompson* (Hipodrom, 5 July) and *Kirk* (10 Sept) — if `trends_iot_*.csv` exist after `trends-run` |
| 8 | “Contested event” | Same episode, **different public labels** (riot vs. protest; memory politics) + **low slur salience in Trends** |
| 9 | **2025 anchors (optional slide)** | **Thompson** concert Zagreb; **Kirk** assassination US — *dates in config; Trends curves optional* |
| 10 | Limitations | Trends **0–100**; Event Registry **free tier**; GKG = coarse substring counts; **no** causal claim |
| 11 | Next step | Refine **CQL** (lemmata, diacritics, near-synonyms); `gdelt-snapshot` for BigQuery cross-check; `output/methodology_diagrams.md` |

*Wikipedia numbers from the latest `wiki_batch_*.json` in `data/raw/`. Regenerate: `python -m pipeline run-free` then `python -m pipeline refresh-output`.*

---

## 5. Key numbers to say aloud

**Explanation:** This section is **speaker notes**: short **numeric anchors** you can quote in Q&A. Each bullet ties to a **different instrument**, so rehearse the **one-sentence caveat** per bullet (Wikipedia = article choice; ER = index + window; hrWac = token in web corpus; Trends = relative and often zero for slurs). The **spike ratios** in the Trends line come from **`trends_summary_*.json`**: “max around event” divided by “mean outside window” for a ±3 day band in the **legacy demo** windows—see those JSON files for exact definitions.

- **Wikipedia (90 days):** EN *Political polarization* **{en_sum:,}** total daily views; HR *Hrvatska* **{hr_sum:,}** (attention context).
- **Event Registry (indexed news, last batch):** e.g. **MAGA** ~**{maga_hits:,}** total hits; **Ustaše** **{ustase_hits:,}**; several HR terms **0** in the same search setup — *interpret as “sparse in that index + window”, not as “unused in society”.*
- {sk_b}
- **Trends (spike ratio ±3 days around event, legacy demo windows):** *Capitol riot* **~{cap_r:.2f}**; *January 6th* **~{jan6:.2f}**; *MAGA* **~{maga_r:.2f}**; *libtard* **{lib_r:.1f}**; *Stop the Steal* **~{st_s:.2f}**; *Oluja* **~{ol_r:.1f}**; *Ustaše* **{usta_trend:.1f}** in Trends.

Full table: `output/presentation_metrics.csv`
Trends detail: `output/trends_spike_summary.csv`
Event Registry: `output/eventregistry_snapshot.csv`
Methodology: `output/methodology_diagrams.md` — `output/HANDOFF_execute_without_bigquery.md` (scope when skipping BigQuery)

---

## 6. Figures you can show (export from project data)

**Explanation:** Each item is a **ready-made export path** (CSV/JSON) you can plot in Excel, R, or Python. **Line charts (1–3)** are for **temporal** narrative: show the **event date** as a vertical rule so the audience sees **co-movement** (or lack of it) with slur strings. **Bar chart (4)** summarises **spike ratios** across keywords—good for “mainstream label vs slur string” contrast. **Tables (5–6)** are for **index-level** comparisons (ER totals vs hrWac **N**): stress that **units differ** (article hits vs concordance lines).

1. **Line chart:** `data/processed/trends_iot_us_capitol_contested_2021.csv` — mark **2021-01-06** vertical line.
2. **Line chart:** `data/processed/trends_iot_hr_oluja_window_2024.csv` — mark **2024-08-05** (Oluja).
3. **Optional 2025:** `data/processed/trends_iot_hr_thompson_hipodrom_2025.csv` and `data/processed/trends_iot_us_kirk_2025.csv` (after `trends-run`) — mark **2025-07-05** and **2025-09-10** if the series are non-empty.
4. **Bar chart:** `trends_spike_summary.csv` — *ratio* (drop zeros for slur-focused story).
5. **Table:** `eventregistry_snapshot.csv` — *total_results* by term (caveat on index).
6. **Table (corpus N):** `data/processed/sketch_hrwac_slurs.json` — **word-form** **N** per HRV slur; optional mini KWIC lines in the same file (FUP — do not re-scrape the corpus at scale outside Sketch rules).

---

## 7. One-minute “limitations” monologue (honest, referee-proof)

**Explanation:** Use this block as a **verbatim** or **paraphrased** closing if a referee asks “what are you *not* claiming?”. It restates **instrument limits** (Trends suppression, ER archive, GKG coarseness, hrWac as **written web** only) and repeats that **alignment** in time is **exploratory**.

{sketch_limitation_bullet}
- **Google Trends** is **not** official or absolute volume; **slurs** are often **hidden or zero**.
- **Event Registry** depends on **plan**, **time window**, and **keyword**; free tier is **not** full archive.
- **GDELT** requires GCP billing on many accounts; use **short** date windows; interpret GKG as approximate.
- **Alignment** of curves and events is **exploratory** — not causal inference.

---

## 8. How to refresh this report

**Explanation:** This section is **only** the **command sequence** to reproduce the CSV/MD artefacts. It does **not** replace **§1–§7** for interpretation. Run commands from the project root with the venv activated; see **§9** for what each step reads and writes.

**Full stack (all layers):** run the block below top to bottom. **Event Registry** needs `EVENTREGISTRY_API_KEY` in `.env`. **Sketch / hrWac** needs `SKETCH_ENGINE_USER` and `SKETCH_ENGINE_KEY`. **GDELT** needs `pip install -e ".[gdelt]"` once, then `GOOGLE_CLOUD_PROJECT` plus BigQuery auth (`GOOGLE_APPLICATION_CREDENTIALS` or ADC); if GDELT is skipped, the report still builds.

```bash
cd slurs_cer_julija
source .venv/bin/activate
python -m pipeline run-free
python -m pipeline er-batch
python -m pipeline er-summarize
python -m pipeline trends-run
python -m pipeline sketch-slurs
# One-time (or after upgrades): pip install -e ".[gdelt]"
python -m pipeline gdelt-snapshot
python -m pipeline refresh-output
```

---

{process_guide_block}
---

*Main files: `presentation_report.md`, `presentation_metrics.csv`, `trends_spike_summary.csv`, `eventregistry_snapshot.csv`, `data/processed/sketch_hrwac_slurs.json` (after `sketch-slurs`), `data/processed/gdelt_summary_*.json` (after `gdelt-snapshot`), `methodology_diagrams.md`.*
"""


__all__ = ["refresh_output_dir"]
