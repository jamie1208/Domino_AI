"""Offline test coverage for TWSE official company profile connector."""
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db_models import Base, CompanyRecord, GraphEdgeRecord
from app.ingestion.twse_companies import import_twse_snapshot
from app.skills.twse_companies import (
    CompanySourceError, TWSE_COMPANY_API, TWSECompanyConnector,
    parse_twse_profiles,
)

NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


def payload(name="合成測試公司", industry="半導體業"):
    return json.dumps([
        {"公司代號": "2330", "公司名稱": name, "產業別": industry, "出表日期": "1151016"}
    ], ensure_ascii=False).encode("utf-8")


def test_parses_official_field_names_with_cautious_source_dates():
    snapshot = parse_twse_profiles(payload(), retrieved_at=NOW)
    assert len(snapshot.profiles) == 1
    company = snapshot.profiles[0]
    assert company.company_key == "twse-listed:2330"
    assert company.name == "合成測試公司"
    assert company.market == "listed"
    assert company.source_report_date_raw == "1151016"
    assert snapshot.retrieved_at == NOW


def test_fetch_uses_single_fixed_api_and_blocks_redirects():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=payload())

    snapshot = TWSECompanyConnector(transport=httpx.MockTransport(handler)).fetch()
    assert calls == [TWSE_COMPANY_API]
    assert len(snapshot.profiles) == 1

    redirect = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"Location": "https://other.example/"})
    )
    with pytest.raises(CompanySourceError, match="302"):
        TWSECompanyConnector(transport=redirect).fetch()


def test_malformed_or_empty_feed_fails_closed():
    for response in (b"{}", b"[]", b"<html>Error</html>", b""):
        with pytest.raises(CompanySourceError):
            parse_twse_profiles(response, retrieved_at=NOW)


def test_duplicate_company_code_rejected():
    row = {"公司代號": "2330", "公司名稱": "合成"}
    with pytest.raises(CompanySourceError, match="Duplicate"):
        parse_twse_profiles(json.dumps([row, row]).encode(), retrieved_at=NOW)


def test_invalid_rows_skipped_but_never_fabricated():
    source = json.dumps([
        {"公司代號": "2330", "公司名稱": "合成測試公司"},
        {"公司代號": "??", "公司名稱": "Invalid"},
        {"公司代號": "2317"},
    ], ensure_ascii=False).encode()
    snapshot = parse_twse_profiles(source, retrieved_at=NOW)
    assert len(snapshot.profiles) == 1
    assert snapshot.rejected_rows == 2


def test_oversized_content_length_rejected_before_read():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, headers={"Content-Length": "9000000"}, content=b"[]")
    )
    with pytest.raises(CompanySourceError, match="content-length"):
        TWSECompanyConnector(transport=transport).fetch()


def test_company_import_idempotent_and_versions_on_meaningful_change():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        first = parse_twse_profiles(payload(), retrieved_at=NOW)
        created = import_twse_snapshot(session, first)
        assert created.created_versions == 1
        assert created.unchanged == 0

        repeat = parse_twse_profiles(payload(), retrieved_at=NOW + timedelta(days=1))
        result = import_twse_snapshot(session, repeat)
        assert result.created_versions == 0
        assert result.unchanged == 1

        changed = parse_twse_profiles(payload(name="合成測試公司新名稱"), retrieved_at=NOW + timedelta(days=2))
        result2 = import_twse_snapshot(session, changed)
        assert result2.created_versions == 1
        records = list(session.scalars(select(CompanyRecord).order_by(CompanyRecord.version)))
        assert [r.version for r in records] == [1, 2]
        assert records[0].valid_to == NOW + timedelta(days=2)
        assert records[-1].metadata_json["source_url"] == TWSE_COMPANY_API
        assert records[-1].is_synthetic is False
        assert list(session.scalars(select(GraphEdgeRecord))) == []
        session.rollback()
