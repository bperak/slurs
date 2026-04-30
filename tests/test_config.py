"""Config loads without crashing (optionally with empty .env)."""

from pipeline.config import Settings, get_settings


def test_get_settings() -> None:
    s = get_settings()
    assert isinstance(s, Settings)
    assert s.data_raw.name == "raw"
    assert s.data_processed.name == "processed"
