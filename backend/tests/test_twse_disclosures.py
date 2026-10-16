"""Synthetic offline coverage for official TWSE daily material disclosures."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import os
from uuid import uuid4

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


def test_same_second_same_title_body_but_different_fact_or_clause_is_preserved():
    original = json.loads(payload())[0]
    by_clause = {**original, "符合條款": "第20款"}
    by_fact_date = {**original, "事實發生日": "1150713"}
    by_report_date = {**original, "出表日期": "1151017"}
    rows = [original, by_clause, by_fact_date, by_report_date]
    snapshot = parse_disclosures(json.dumps(rows, ensure_ascii=False).encode(), retrieved_at=NOW)
    assert snapshot.rejected_rows == 0
    assert len(snapshot.documents) == len(rows) == 4
    assert len({doc.document_key for doc in snapshot.documents}) == 4
    assert [m["clause_raw"] for m in snapshot.source_rows][1] == "第20款"
    assert snapshot.source_rows[2]["fact_date_raw"] == "1150713"
    assert snapshot.source_rows[3]["batch_report_date_raw"] == "1151017"


def test_official_five_digit_clock_retained_with_taipei_timezone():
    row = json.loads(payload())[0]
    row["發言時間"] = "64428"
    snapshot = parse_disclosures(json.dumps([row], ensure_ascii=False).encode(), retrieved_at=NOW)
    instant = snapshot.source_published_times[0]
    assert instant.isoformat() == "2026-10-15T06:44:28+08:00"
    assert snapshot.source_rows[0]["speech_time_raw"] == "64428"
    assert snapshot.source_rows[0]["speech_time_normalized"] == "064428"


def test_archive_persists_distinct_source_rows_and_exact_announcement_instant():
    original = json.loads(payload())[0]
    another = {**original, "事實發生日": "1150713", "符合條款": "第20款"}
    first = parse_disclosures(json.dumps([original, another], ensure_ascii=False).encode(), retrieved_at=NOW)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        result = persist_disclosures(session, first)
        assert result["created_versions"] == 2
        stored = list(session.scalars(select(PublicDocumentRecord).order_by(PublicDocumentRecord.document_key)))
        assert len(stored) == 2
        assert {r.source_metadata["fact_date_raw"] for r in stored} == {"1151014", "1150713"}
        assert {r.source_metadata["clause_raw"] for r in stored} == {"第51款", "第20款"}
        assert all(r.source_metadata["canonical_source_row_sha256"] for r in stored)
        assert all(r.source_published_at.replace(tzinfo=timezone.utc).isoformat() == "2026-10-15T01:01:23+00:00" for r in stored)
        assert all(r.source_published_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Asia/Taipei")).strftime("%H%M%S") == "090123" for r in stored)
        assert all(r.verification_status == "unverified" for r in stored)
        assert list(session.scalars(select(GraphEdgeRecord))) == []


def test_same_row_reappears_in_different_batch_hash_without_new_version():
    row = json.loads(payload())[0]
    first = parse_disclosures(json.dumps([row], ensure_ascii=False).encode(), retrieved_at=NOW)
    second = parse_disclosures(json.dumps([row, {**row, "公司代號": "2317"}], ensure_ascii=False).encode(), retrieved_at=NOW + timedelta(days=1))
    assert first.payload_sha256 != second.payload_sha256
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        assert persist_disclosures(session, first)["created_versions"] == 1
        counts = persist_disclosures(session, second)
        assert counts == {"created_versions": 1, "unchanged": 1}
        assert len(list(session.scalars(select(PublicDocumentRecord)))) == 2


def test_conflicting_normalized_source_keys_fail_closed():
    row = json.loads(payload())[0]
    row["主旨"] = "另一種標題"
    with pytest.raises(DisclosureSourceError, match="zero valid"):
        parse_disclosures(json.dumps([row], ensure_ascii=False).encode(), retrieved_at=NOW)


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="isolated migrated PostgreSQL schema required")
def test_postgres_distinct_same_second_disclosures_keep_provenance():
    original = json.loads(payload())[0]
    code = "T" + uuid4().hex[:7]
    original["公司代號"] = code
    alternate = {**original, "符合條款": "第20款", "事實發生日": "1150713"}
    snapshot = parse_disclosures(
        json.dumps([original, alternate], ensure_ascii=False).encode(),
        retrieved_at=NOW,
    )
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    with Session(engine) as session:
        assert persist_disclosures(session, snapshot)["created_versions"] == 2
        records = list(session.scalars(
            select(PublicDocumentRecord)
            .where(PublicDocumentRecord.company_key == f"twse-listed:{code}")
        ))
        assert len(records) == 2
        assert records[0].source_published_at is not None
        assert all(row.source_metadata["canonical_source_row"] for row in records)
        assert len({row.source_metadata["canonical_source_row_sha256"] for row in records}) == 2
        assert all(row.source_published_at.astimezone(ZoneInfo("Asia/Taipei")).strftime("%H%M%S") == "090123" for row in records)
        assert list(session.scalars(
            select(GraphEdgeRecord).where(GraphEdgeRecord.edge_key == f"twse-material:{code}")
        )) == []
        session.rollback()
