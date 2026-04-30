"""Flatten Event Registry article JSON to evidence rows (no HTTP)."""

from pipeline.ingest.eventregistry import response_to_table_rows


def test_response_to_table_rows() -> None:
    data = {
        "articles": {
            "results": [
                {
                    "date": "2026-01-01",
                    "dateTime": "2026-01-01T12:00:00Z",
                    "title": "T",
                    "url": "https://x",
                    "lang": "eng",
                    "body": "Hello " * 100,
                    "isDuplicate": False,
                    "dataType": "news",
                    "source": {"uri": "x.com", "title": "X"},
                }
            ]
        }
    }
    rows = response_to_table_rows(data)
    assert len(rows) == 1
    assert rows[0]["source_domain"] == "x.com"
    assert len(rows[0]["body_excerpt"]) <= 3000
