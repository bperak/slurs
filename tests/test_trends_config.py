"""trends_event_windows.json shape (no live API)."""

import json
from pathlib import Path


def test_trends_config_includes_split_folklore_2025() -> None:
    p = Path(__file__).resolve().parent.parent / "config" / "trends_event_windows.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    ids = [r["id"] for r in d.get("runs") or []]
    assert "hr_split_folklore_nov2025" in ids
    run = next(r for r in d["runs"] if r["id"] == "hr_split_folklore_nov2025")
    assert run["event_date"] == "2025-11-03"
    assert run["geo"] == "HR"
    assert len(run["keywords"]) <= 5


def test_anchor_events_folklore_has_date() -> None:
    p = Path(__file__).resolve().parent.parent / "config" / "anchor_events.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    folk = next(x for x in d["croatia"] if x.get("id") == "folklore_attack")
    assert folk.get("approx_date") == "2025-11-03"
    assert "Split" in (folk.get("location") or "")


def test_anchor_antifascist_nov30() -> None:
    p = Path(__file__).resolve().parent.parent / "config" / "anchor_events.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    ant = next(x for x in d["croatia"] if x.get("id") == "antifascist_protest")
    assert ant.get("approx_date") == "2025-11-30"
    assert "Ujedinjeni" in (ant.get("label") or "") or "fašiz" in (ant.get("label") or "").lower()


def test_trends_config_ujedinjeni_run() -> None:
    p = Path(__file__).resolve().parent.parent / "config" / "trends_event_windows.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    ids = [r["id"] for r in d.get("runs") or []]
    assert "hr_ujedinjeni_protiv_fasizma_nov2025" in ids
    run = next(r for r in d["runs"] if r["id"] == "hr_ujedinjeni_protiv_fasizma_nov2025")
    assert run["event_date"] == "2025-11-30"
    assert len(run["keywords"]) <= 5
