"""Event Registry batch skips cleanly when no API key."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.batch_eventregistry import run_batch


def test_run_batch_skips_when_no_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    m = MagicMock()
    m.has_eventregistry = False
    m.data_raw = tmp_path / "raw"
    m.data_raw.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("pipeline.batch_eventregistry.get_settings", lambda: m)
    cfg = {
        "queries": [{"id": "x", "keyword": "test", "lang": "eng"}],
        "eventregistry_defaults": {},
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    logp = run_batch(config_path=p, dry_run=False, summarize_after=False)
    log = json.loads(logp.read_text(encoding="utf-8"))
    assert "skipped" in log
    assert log["ok"] is False
