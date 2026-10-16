"""Synthetic offline coverage for official TWSE daily material disclosures."""
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db_models import Base, PublicDocumentRecord, DocumentChunkRecord, GraphEdgeRecord
from app.ingestion.import_twse_disclosures import persist_disclosures
from app.skills.twse_disclosures import (
    TWSEDisclosureConnector, DisclosureSourceError, parse_disclosures, URL,
)

NOW = datetime(2026, 10, 16, 4, tzinfo=timezone.utc)


def payload(*, title="合成重大訊息", content="合成半導體材料公告。", code="2330"):
    return json.dumps([{
        "出表日期": "1151016", "發言日期": "1151015",
        "發言時間": "090123", "公司代號": code,
        "公司名稱": "測試公司", "主旨 ": title,
        "符合條款": "第51款", "事實發生日": "1151014",
        "說明": content,
    }], ensure_ascii=False).encode("utf-8")


def test_publication_date_not_fact_or_batch_date():
    snapshot = parse_disclosures(payload(), retrieved_at=NOW)
    doc = snapshot.documents[0]
    assert doc.published_at == "2026-10-15"
    assert doc.company_key == "twse-listed:2330"
    assert doc.source_url == URL
    assert doc.source_type == "material_announcement"
    assert doc.title == "合成重大訊息"
    assert snapshot.rejected_rows == 0


def test_response_schema_handles_trailing_space_and_stable_ids():
    one = parse_disclosures(payload(), retrieved_at=NOW).documents[0]
    two = parse_disclosures(payload(), retrieved_at=NOW + timedelta(days=1)).documents[0]
    assert one.document_key == two.document_key


def test_different_same_second_announcements_are_not_dropped():
    one = json.loads(payload())[0]
    two = {**one, "主旨 ": "另外一則公告"}
    result = parse_disclosures(
        json.dumps([one, two], ensure_ascii=False).encode(), retrieved_at=NOW
    )
    assert len(result.documents) == 2
    assert len({doc.document_key for doc in result.documents}) == 2


def test_fixed_endpoint_and_no_redirect_follow():
    calls = []
    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, content=payload())
    assert len(TWSEDisclosureConnector(transport=httpx.MockTransport(handler)).fetch().documents) == 1
    assert calls == [URL]
    with pytest.raises(DisclosureSourceError, match="302"):
        TWSEDisclosureConnector(transport=httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"Location": "https://other.example/"})
        )).fetch()


def test_timeout_and_unbounded_stream_fail_closed():
    def timed_out(req):
        raise httpx.ReadTimeout("synthetic timeout", request=req)
    with pytest.raises(DisclosureSourceError, match="unavailable"):
        TWSEDisclosureConnector(transport=httpx.MockTransport(timed_out)).fetch()

    class Oversize(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 12_000_001
    with pytest.raises(DisclosureSourceError, match="body too large"):
        TWSEDisclosureConnector(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, stream=Oversize())
        )).fetch()


def test_empty_snapshot_valid_but_invalid_nonempty_fails():
    empty = parse_disclosures(b"[]", retrieved_at=NOW)
    assert empty.documents == ()
    with pytest.raises(DisclosureSourceError, match="zero valid"):
        parse_disclosures(json.dumps([{"other": "field"}]).encode(), retrieved_at=NOW)
    with pytest.raises(DisclosureSourceError):
        parse_disclosures(b"<html>error</html>", retrieved_at=NOW)


def test_realistic_schema_rejects_missing_publication_date_not_guess():
    row = json.loads(payload())[0]
    row.pop("發言日期")
    with pytest.raises(DisclosureSourceError, match="zero valid"):
        parse_disclosures(json.dumps([row], ensure_ascii=False).encode(), retrieved_at=NOW)


def test_transactional_import_deduplicates_and_preserves_unverified_text():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    snapshot = parse_disclosures(payload(), retrieved_at=NOW)
    with Session(engine) as session:
        assert persist_disclosures(session, snapshot)["created_versions"] == 1
        later = parse_disclosures(payload(), retrieved_at=NOW + timedelta(days=1))
        assert persist_disclosures(session, later)["unchanged"] == 1
        rows = list(session.scalars(select(PublicDocumentRecord)))
        assert len(rows) == 1
        assert rows[0].verification_status == "unverified"
        assert rows[0].original_text == "合成半導體材料公告。"
        assert len(list(session.scalars(select(DocumentChunkRecord)))) == 1
        assert list(session.scalars(select(GraphEdgeRecord))) == []
