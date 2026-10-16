"""Offline CLI input tests: no external URL is fetched."""
import json

import pytest

from app.ingestion.import_public_document import read_import_file


def _payload():
    return {
        "document_key": "twse-report:test-2026-10",
        "company_key": "twse-listed:2330",
        "title": "合成營運揭露",
        "source_url": "https://disclosure.example/filing",
        "published_at": "2026-10-10",
        "text": "僅供測試的企業揭露內容。\n" * 10,
        "source_type": "company_disclosure",
    }


def test_operator_json_input_accepted(tmp_path):
    path = tmp_path / "document.json"
    path.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    doc = read_import_file(path)
    assert doc.company_key == "twse-listed:2330"
    assert "僅供測試" in doc.text


def test_operator_json_rejects_extra_metadata(tmp_path):
    path = tmp_path / "document.json"
    bad = {**_payload(), "independently_verified": True}
    path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata keys"):
        read_import_file(path)


def test_operator_json_rejects_invalid_source(tmp_path):
    path = tmp_path / "document.json"
    bad = {**_payload(), "source_url": "file:///tmp/secret"}
    path.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="HTTPS"):
        read_import_file(path)


def test_operator_json_rejects_oversize(tmp_path):
    path = tmp_path / "document.json"
    path.write_bytes(b"x" * 1_000_001)
    with pytest.raises(ValueError, match="1 MB"):
        read_import_file(path)
