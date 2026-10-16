from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api_adapter import adapt_analysis
from app.db_models import Base, DataChangeLogRecord
from app.fixture import FixtureProvider
from app.orchestrator import Orchestrator
from app.persistence import AnalysisPersistenceService
from app.repositories import CompanyRepository, EvidenceRepository, GraphRepository
from app.repositories.graph import InvalidGraphRelationshipError
from app.schemas import Scenario


@pytest.fixture
def session():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def test_company_versions_and_temporal_lookup(session):
    repo = CompanyRepository(session)
    first_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_at = first_at + timedelta(days=30)
    repo.create_version(company_key='synthetic-a', name='合成企業 A', valid_from=first_at, is_synthetic=True)
    repo.create_version(company_key='synthetic-a', name='合成企業 A（新版）', valid_from=second_at, is_synthetic=True)
    session.commit()
    assert repo.get_at('synthetic-a', first_at + timedelta(days=1)).name == '合成企業 A'
    assert repo.get_at('synthetic-a', second_at + timedelta(days=1)).name == '合成企業 A（新版）'
    assert [item.version for item in repo.history('synthetic-a')] == [1, 2]


def test_evidence_update_is_non_lossy_and_prevents_future_leakage(session):
    repo = EvidenceRepository(session)
    first_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    second_at = first_at + timedelta(days=30)
    first = repo.create_version(evidence_id='synthetic-e1', title='合成證據', content='版本一', kind='industry_model', verification_status='supported', supports_claim=True, published_at=first_at, retrieved_at=first_at, valid_from=first_at)
    duplicate = repo.create_version(evidence_id='synthetic-e1', title='合成證據', content='版本一', kind='industry_model', verification_status='supported', supports_claim=True, published_at=first_at, retrieved_at=first_at, valid_from=first_at)
    repo.create_version(evidence_id='synthetic-e1', title='合成證據新版', content='版本二', kind='industry_model', verification_status='supported', supports_claim=True, published_at=second_at, retrieved_at=second_at, valid_from=second_at)
    session.commit()
    assert duplicate.id == first.id
    assert len(repo.history('synthetic-e1')) == 2
    assert repo.get_at('synthetic-e1', first_at + timedelta(days=1)).content_hash == first.content_hash
    assert repo.get_at('synthetic-e1', first_at - timedelta(days=1)) is None


def test_graph_relationship_evidence_gate_and_candidate_exclusion(session):
    graph = GraphRepository(session)
    evidence = EvidenceRepository(session)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    source = graph.create_node_version(node_key='industry-a', kind='industry', label='合成產業 A', valid_from=now, data_version='test-v1')
    target = graph.create_node_version(node_key='industry-b', kind='industry', label='合成產業 B', valid_from=now, data_version='test-v1')
    with pytest.raises(InvalidGraphRelationshipError):
        graph.create_edge_version(edge_key='candidate', source_node_id=source.id, target_node_id=target.id, relation_kind='unverified_candidate', propagation_eligible=True, valid_from=now, data_version='test-v1')
    unverified = evidence.create_version(evidence_id='synthetic-unverified', title='未驗證合成證據', content='候選', kind='unverified', verification_status='unverified', supports_claim=False, retrieved_at=now, valid_from=now)
    with pytest.raises(InvalidGraphRelationshipError):
        graph.create_edge_version(edge_key='direct', source_node_id=source.id, target_node_id=target.id, relation_kind='verified_direct', propagation_eligible=True, evidence_record_ids=[unverified.id], valid_from=now, data_version='test-v1')
    industry = evidence.create_version(evidence_id='synthetic-industry', title='合成產業模型證據', content='產業推論', kind='industry_model', verification_status='supported', supports_claim=True, retrieved_at=now, valid_from=now)
    with pytest.raises(InvalidGraphRelationshipError):
        graph.create_edge_version(edge_key='direct', source_node_id=source.id, target_node_id=target.id, relation_kind='verified_direct', propagation_eligible=True, evidence_record_ids=[industry.id], valid_from=now, data_version='test-v1')
    supported = evidence.create_version(evidence_id='synthetic-supported', title='已支持合成證據', content='支持', kind='official', verification_status='supported', supports_claim=True, retrieved_at=now, valid_from=now)
    edge = graph.create_edge_version(edge_key='direct', source_node_id=source.id, target_node_id=target.id, relation_kind='verified_direct', propagation_eligible=True, evidence_record_ids=[supported.id], valid_from=now, data_version='test-v1')
    session.commit()
    assert edge in graph.edges_at(now + timedelta(seconds=1), propagation_only=True)


def test_analysis_snapshot_round_trip_without_recalculation(session):
    scenario = Scenario(description='合成材料中斷', severity=.8, seed_nodes=['材料產業'])
    api_result = adapt_analysis(Orchestrator(FixtureProvider()).run(scenario, data_mode='fixture'))
    service = AnalysisPersistenceService(session)
    service.save(api_result)
    stored = service.get(api_result.analysis_id)
    assert stored == api_result
    first_change_count = session.scalar(select(func.count()).select_from(DataChangeLogRecord))
    service.save(api_result)
    assert session.scalar(select(func.count()).select_from(DataChangeLogRecord)) == first_change_count


def test_missing_risk_is_persisted_as_null(session):
    api_result = adapt_analysis(Orchestrator(FixtureProvider()).run(Scenario(description='合成材料中斷'), data_mode='fixture'))
    service = AnalysisPersistenceService(session)
    service.save(api_result)
    assert service.get(api_result.analysis_id).risk_results == []
