"""GDELT summary rows feed the report (no live BigQuery in CI)."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.refresh_output import _gdelt_presentation


def test_gdelt_presentation_from_fixture(tmp_path: Path) -> None:
    proc = tmp_path / "processed"
    proc.mkdir()
    summary = {
        "project": "test",
        "runs": [
            {
                "id": "demo_run",
                "gkg_record_count_theme_match": 42,
                "partition_start": "2025-07-01",
                "partition_end": "2025-07-10",
            }
        ],
    }
    (proc / "gdelt_summary_2099-01-01.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    h2, rows = _gdelt_presentation(proc)
    assert "42" in h2
    assert rows and rows[0]["section"] == "GDELT GKG (BigQuery)"


def test_gdelt_presentation_missing_file(tmp_path: Path) -> None:
    h2, rows = _gdelt_presentation(tmp_path)
    assert "Not in this run" in h2
    assert rows == []
