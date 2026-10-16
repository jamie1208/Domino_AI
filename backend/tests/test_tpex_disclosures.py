"""Offline regressions for TPEx material-disclosure ingestion."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from zoneinfo import ZoneInfo
from uuid import uuid4
import json
import os

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db_models import Base, PublicDocumentRecord, GraphEdgeRecord, AnalysisResultRecord
from app.ingestion.import_twse_disclosures import persist_disclosures
from app.skills.tpex_disclosures import (
    TPEX_DISCLOSURE_URL, TPExDisclosureConnector, parse_tpex_disclosures,
)
from app.skills.twse_disclosures import DisclosureSourceError, parse_disclosures

NOW = datetime(2026, 10, 16, 8, tzinfo=timezone.utc)


def payload(*, code="6488", clock="64428"):
    return json.dumps([{
        "出表日期": "1151016", "發言日期": "1151015",
        "發言時間": clock, "公司代號": code,
        "公司名稱": "合成上櫃企業", "主旨 ": "合成營運公告",
        "符合條款": "第20款", "事實發生日": "1150713",
        "說明": "合成半導體材料供應相關資訊",
    }], ensure_ascii=False).encode("utf-8")


def test_tpex_market_scoped_identity_source_and_taiwan_instant():
    source = parse_tpex_disclosures(payload(), retrieved_at=NOW)
    row = source.documents[0]
    assert row.company_key == "tpex-otc:6488"
    assert row.document_key.startswith("tpex-material:6488:")
    assert row.source_url == TPEX_DISCLOSURE_URL
    assert row.published_at == "2026-10-15"
    assert source.source_published_times[0].isoformat() == "2026-10-15T06:44:28+08:00"
    assert source.source_rows[0]["speech_time_normalized"] == "064428"
    assert "主旨 " in source.source_rows[0]["canonical_source_row"]
    assert "主旨" in source.source_rows[0]["normalized_source_row"]


def test_same_ticker_twse_and_tpex_never_share_document_identity():
    raw = payload()
    otc = parse_tpex_disclosures(raw, retrieved_at=NOW)
    listed = parse_disclosures(raw, retrieved_at=NOW)
    assert otc.documents[0].company_key != listed.documents[0].company_key
    assert otc.documents[0].document_key != listed.documents[0].document_key


def test_same_second_different_clause_or_fact_date_preserves_both():
    original = json.loads(payload())[0]
    altered = {**original, "符合條款": "第51款", "事實發生日": "1151014"}
    snapshot = parse_tpex_disclosures(
        json.dumps([original, altered], ensure_ascii=False).encode(), retrieved_at=NOW
    )
    assert len(snapshot.documents) == 2
    assert len({d.document_key for d in snapshot.documents}) == 2
    for i, item in enumerate(snapshot.source_rows):
        canonical = json.dumps(
            item["canonical_source_row"], ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        assert item["canonical_source_row_sha256"] == sha256(canonical.encode()).hexdigest()


def test_fetch_single_fixed_official_endpoint_and_reject_redirect():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=payload())
    connector = TPExDisclosureConnector(transport=httpx.MockTransport(handler))
    assert len(connector.fetch().documents) == 1
    assert calls == [TPEX_DISCLOSURE_URL]
    with pytest.raises(DisclosureSourceError, match="302"):
        TPExDisclosureConnector(transport=httpx.MockTransport(
            lambda req: httpx.Response(302, headers={"Location": "https://wrong.example"})
        )).fetch()


def test_fetch_timeout_and_streamed_excess_fail_closed():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)
    with pytest.raises(DisclosureSourceError, match="unavailable"):
        TPExDisclosureConnector(transport=httpx.MockTransport(handler)).fetch()

    class LargeStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 12_000_001

    with pytest.raises(DisclosureSourceError, match="body too large"):
        TPExDisclosureConnector(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, stream=LargeStream())
        )).fetch()


def test_unsupported_schema_or_invalid_date_fail_closed():
    for body in (b"", b"{}", b"<html>denied</html>"):
        with pytest.raises(DisclosureSourceError):
            parse_tpex_disclosures(body, retrieved_at=NOW)
    bad = json.loads(payload())[0]
    bad["發言日期"] = "bad"
    with pytest.raises(DisclosureSourceError, match="zero valid"):
        parse_tpex_disclosures(json.dumps([bad], ensure_ascii=False).encode(), retrieved_at=NOW)


def test_tpex_archive_dedup_with_different_batch_and_no_relations():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    original = json.loads(payload())[0]
    first = parse_tpex_disclosures(payload(), retrieved_at=NOW)
    second = parse_tpex_disclosures(
        json.dumps([original, {**original, "公司代號": "6489"}], ensure_ascii=False).encode(),
        retrieved_at=NOW + timedelta(days=1),
    )
    with Session(engine) as session:
        assert persist_disclosures(session, first)["created_versions"] == 1
        assert persist_disclosures(session, second) == {"created_versions": 1, "unchanged": 1}
        rows = list(session.scalars(select(PublicDocumentRecord)))
        assert len(rows) == 2
        assert all(r.verification_status == "unverified" for r in rows)
        assert all(r.source_published_at is not None for r in rows)
        assert all(r.source_metadata["fact_date_raw"] == "1150713" for r in rows)
        assert list(session.scalars(select(GraphEdgeRecord))) == []
        assert list(session.scalars(select(AnalysisResultRecord))) == []


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL test schema required")
def test_postgres_tpex_announcement_provenance():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    code = "Q" + uuid4().hex[:7]
    original = json.loads(payload(code=code))[0]
    other = {**original, "事實發生日": "1151014"}
    snapshot = parse_tpex_disclosures(
        json.dumps([original, other], ensure_ascii=False).encode(), retrieved_at=NOW,
    )
    with Session(engine) as session:
        assert persist_disclosures(session, snapshot)["created_versions"] == 2
        records = list(session.scalars(
            select(PublicDocumentRecord).where(PublicDocumentRecord.company_key == f"tpex-otc:{code}")
        ))
        assert len(records) == 2
        assert all(r.source_metadata["canonical_source_row"] for r in records)
        assert all(r.source_published_at.astimezone(ZoneInfo("Asia/Taipei")).strftime("%H%M%S") == "064428" for r in records)
        session.rollback()
