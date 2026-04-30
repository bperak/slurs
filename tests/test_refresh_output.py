"""Refresh output regenerates CSVs and report from data/."""

from __future__ import annotations

from pathlib import Path

from pipeline.refresh_output import refresh_output_dir


def test_refresh_output_writes_files(tmp_path: Path) -> None:
    project = Path(__file__).resolve().parent.parent
    data_proc = project / "data" / "processed"
    data_raw = project / "data" / "raw"
    out = tmp_path / "out"
    written = refresh_output_dir(out, data_processed=data_proc, data_raw=data_raw)
    assert (out / "presentation_report.md").is_file()
    assert (out / "presentation_metrics.csv").is_file()
    text = (out / "presentation_report.md").read_text(encoding="utf-8")
    assert "Slurs, polarization" in text
    assert "Wikipedia" in (out / "presentation_metrics.csv").read_text(encoding="utf-8")
    assert all(p.exists() for p in written)
