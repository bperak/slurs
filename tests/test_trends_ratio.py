"""Spike ratio helper (no pytrends network)."""

import pandas as pd

from pipeline.ingest.google_trends import add_event_ratio


def test_add_event_ratio() -> None:
    idx = pd.date_range("2021-01-01", periods=10, freq="D")
    df = pd.DataFrame({"MAGA": [10] * 10}, index=idx)
    df.loc[idx[5], "MAGA"] = 100
    out = add_event_ratio(df, "2021-01-06", window_days=1)
    assert "MAGA" in out["by_keyword"]
    assert out["by_keyword"]["MAGA"]["max_around_event"] >= 100
