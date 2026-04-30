"""Sketch CQL validation (no network)."""

import pytest

from pipeline.ingest import sketchengine


def test_fetch_concordance_rejects_bare_word() -> None:
    with pytest.raises(ValueError, match="CQL must start with q"):
        sketchengine.fetch_concordance("Hrvatska")


def test_croatian_default_corpus_id() -> None:
    assert "hrwac" in sketchengine.CROATIAN_WEB_CORPUS_DEFAULT.lower()


def test_cql_word_form_escapes() -> None:
    assert sketchengine.cql_word_form("Ustaše") == 'q[word="Ustaše"]'
    assert sketchengine.cql_word_form('say "hi"') == 'q[word="say \\"hi\\""]'
