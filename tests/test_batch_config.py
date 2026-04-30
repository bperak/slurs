"""Config shape and summarizer (no live API)."""

import json
from pathlib import Path

from pipeline.batch_eventregistry import DEFAULT_CONFIG, _load_config
from pipeline.summarize import summarize_eventregistry_raw


def test_load_slurs_terms() -> None:
    cfg = _load_config(DEFAULT_CONFIG)
    assert cfg["version"] == 1
    assert len(cfg["queries"]) >= 1
    for q in cfg["queries"]:
        assert q.get("id")
        assert q.get("keyword")
        assert q.get("lang")


def test_summarize_reads_evidence_json(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    sample = {
        "articles": {
            "totalResults": 12,
            "count": 2,
            "page": 1,
            "pages": 2,
            "results": [],
        }
    }
    (raw / "eventregistry_evidence_test_eng.json").write_text(
        json.dumps(sample), encoding="utf-8"
    )
    df = summarize_eventregistry_raw(raw)
    assert len(df) == 1
    assert int(df.iloc[0]["total_results"]) == 12
