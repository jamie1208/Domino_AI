"""Offline TPEx and multi-source ingestion regression tests."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db_models import Base, CompanyRecord, GraphEdgeRecord, SourceIngestionRunRecord
from app.ingestion.import_company_profiles import persist_snapshot
from app.skills.tpex_companies import (
    TPExCompanyConnector, TPEX_COMPANY_API, parse_tpex_profiles,
)
from app.skills.twse_companies import CompanySourceError, parse_twse_profiles

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def sample_tpex(name="上櫃合成公司", code="6488"):
    return json.dumps([
        {"SecuritiesCompanyCode": code, "CompanyName": name,
         "SecuritiesIndustryCode": "24", "Date": "1151016"},
    ], ensure_ascii=False).encode("utf-8")


def sample_twse(code="6488"):
    return json.dumps([
        {"公司代號": code, "公司名稱": "上市合成公司", "產業別": "電子業", "出表日期": "1151016"}
    ], ensure_ascii=False).encode("utf-8")


def test_tpex_english_schema_and_market_identity():
    snapshot = parse_tpex_profiles(sample_tpex(), retrieved_at=NOW)
    assert snapshot.profiles[0].company_key == "tpex-otc:6488"
    assert snapshot.profiles[0].ticker == "6488"
    assert snapshot.profiles[0].market == "otc"
    assert snapshot.profiles[0].industry == "24"
    assert snapshot.profiles[0].source_report_date_raw == "1151016"
    assert snapshot.source_url == TPEX_COMPANY_API


def test_tpex_fixed_url_no_redirect():
    calls = []
    def ok(req):
        calls.append(str(req.url))
        return httpx.Response(200, content=sample_tpex())
    assert len(TPExCompanyConnector(transport=httpx.MockTransport(ok)).fetch().profiles) == 1
    assert calls == [TPEX_COMPANY_API]
    transport = httpx.MockTransport(
        lambda req: httpx.Response(302, headers={"Location": "https://untrusted.example"})
    )
    with pytest.raises(CompanySourceError, match="302"):
        TPExCompanyConnector(transport=transport).fetch()


def test_tpex_timeout_and_missing_header_oversize():
    def timeout(req):
        raise httpx.ReadTimeout("offline test", request=req)
    with pytest.raises(CompanySourceError, match="unavailable"):
        TPExCompanyConnector(transport=httpx.MockTransport(timeout)).fetch()

    class LargeStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"x" * 8_000_001

    with pytest.raises(CompanySourceError, match="size budget"):
        TPExCompanyConnector(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, stream=LargeStream()))
        ).fetch()


def test_tpex_invalid_data_fails_closed():
    for value in (b"", b"{}", b"[]", b"<html>denied</html>"):
        with pytest.raises(CompanySourceError):
            parse_tpex_profiles(value)
    duplicate = json.dumps([
        {"SecuritiesCompanyCode": "6488", "CompanyName": "公司一"},
        {"SecuritiesCompanyCode": "6488", "CompanyName": "公司二"},
    ], ensure_ascii=False).encode()
    with pytest.raises(CompanySourceError, match="Duplicate"):
        parse_tpex_profiles(duplicate)


def test_both_markets_have_unique_keys_and_successful_receipts():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        listed = parse_twse_profiles(sample_twse(), retrieved_at=NOW)
        otc = parse_tpex_profiles(sample_tpex(), retrieved_at=NOW)
        assert persist_snapshot(session, source_key="twse", snapshot=listed).created_versions == 1
        assert persist_snapshot(session, source_key="tpex", snapshot=otc).created_versions == 1
        assert persist_snapshot(session, source_key="tpex", snapshot=replace(otc, retrieved_at=NOW + timedelta(days=1))).unchanged == 1
        companies = list(session.scalars(select(CompanyRecord)))
        receipts = list(session.scalars(select(SourceIngestionRunRecord)))
        assert {x.company_key for x in companies} == {"twse-listed:6488", "tpex-otc:6488"}
        assert len(receipts) == 3
        assert receipts[-1].created_versions == 0
        assert receipts[-1].unchanged_rows == 1
        assert receipts[-1].payload_sha256 == otc.payload_sha256
        assert list(session.scalars(select(GraphEdgeRecord))) == []


def test_source_identity_forgery_rejected():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    snapshot = parse_tpex_profiles(sample_tpex(), retrieved_at=NOW)
    forged = replace(snapshot, profiles=(replace(snapshot.profiles[0], market="listed"),))
    with Session(engine) as session:
        with pytest.raises(ValueError, match="mismatched"):
            persist_snapshot(session, source_key="tpex", snapshot=forged)
        session.rollback()
        assert list(session.scalars(select(CompanyRecord))) == []


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="isolated PostgreSQL TEST_DATABASE_URL required")
def test_postgres_multi_source_versioning_and_receipts():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    unique = uuid4().hex[:8]
    twse = parse_twse_profiles(sample_twse(), retrieved_at=NOW)
    tpex = parse_tpex_profiles(sample_tpex(), retrieved_at=NOW)
    listed = replace(twse, profiles=(replace(twse.profiles[0], company_key=f"twse-listed:test-{unique}"),))
    otc = replace(tpex, profiles=(replace(tpex.profiles[0], company_key=f"tpex-otc:test-{unique}"),))
    with Session(engine) as session:
        assert persist_snapshot(session, source_key="twse", snapshot=listed).created_versions == 1
        assert persist_snapshot(session, source_key="tpex", snapshot=otc).created_versions == 1
        assert persist_snapshot(session, source_key="tpex", snapshot=replace(otc, retrieved_at=NOW + timedelta(days=1))).unchanged == 1
        assert session.scalar(select(SourceIngestionRunRecord).where(SourceIngestionRunRecord.source_key == "tpex").order_by(SourceIngestionRunRecord.recorded_at.desc())) is not None
        assert list(session.scalars(select(GraphEdgeRecord).where(GraphEdgeRecord.edge_key == f"tpex-otc:test-{unique}"))) == []
        session.rollback()
