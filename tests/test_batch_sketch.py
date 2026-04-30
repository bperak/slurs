"""batch_sketch — no network in default tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.batch_sketch import run_hrwac_slurs


def test_run_hrwac_slurs_dry_run_hrv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m = MagicMock()
    m.has_sketch = True
    m.data_processed = tmp_path / "proc"
    m.data_processed.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("pipeline.batch_sketch.get_settings", lambda: m)
    cfg = {
        "version": 1,
        "sleep_seconds_between_requests": 0.1,
        "queries": [
            {"id": "t1", "keyword": "x", "lang": "hrv", "note": "n"},
            {"id": "t2", "keyword": "y", "lang": "eng", "note": ""},
        ],
    }
    p = tmp_path / "slurs_terms.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    out = run_hrwac_slurs(p, pagesize=2, lang_filter="hrv", dry_run=True)
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d.get("dry_run") is True
    assert len(d.get("items") or []) == 1
    assert d["items"][0].get("cql") == 'q[word="x"]'
    assert out.parent == m.data_processed
