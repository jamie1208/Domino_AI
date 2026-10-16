from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api_adapter import adapt_analysis
from app.db_models import Base, GraphEdgeRecord
from app.evidence_policy import EvidenceAdmissionError
from app.orchestrator import Orchestrator
from app.persistence import AnalysisPersistenceService
from app.repositories import EvidenceRepository
from app.schemas import Evidence, EvidenceKind, EvidenceProvenance, Relation, RelationKind, Scenario
from app.skills.researcher import ResearchBundle


class Provider:
    def __init__(self, evidence, evidence_ids):
        self.evidence = evidence
        self.evidence_ids = evidence_ids

    def retrieve(self, scenario):
        return ResearchBundle(self.evidence, [Relation(source='Synthetic A', target='Synthetic B', kind=RelationKind.corroborated_direct, weight=.5, evidence_ids=self.evidence_ids)])


@pytest.fixture
def session():
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def third_party(identifier, url, *, publisher=None, original=None, independent=True):
    return Evidence(id=identifier, title=f'Synthetic {identifier}', source_url=url, published_at='2026-01-01', kind=EvidenceKind.third_party, supports_claim=True, independently_verified=independent, provenance=EvidenceProvenance(publisher_key=publisher, original_source_key=original, independence_basis='publisher_and_original_source' if publisher and original else None))


def analysis_for(evidence, evidence_ids):
    result = Orchestrator(Provider(evidence, evidence_ids)).run(Scenario(description='合成來源獨立性測試', severity=.8, seed_nodes=['Synthetic A']), data_mode='verified_public_data')
    api_result = adapt_analysis(result)
    api_result.data_mode = 'verified_public_data'
    return result, api_result


def assert_direct_relation_rejected(session, skill_result, api_result, expected_repository_code):
    service = AnalysisPersistenceService(session)
    if skill_result.relations:
        with pytest.raises(EvidenceAdmissionError) as caught:
            service.save(api_result)
        assert caught.value.code == expected_repository_code
        session.rollback()
    else:
        service.save(api_result)
    direct_edges = list(session.scalars(select(GraphEdgeRecord).where(GraphEdgeRecord.relation_kind == 'verified_direct')))
    assert direct_edges == []


def test_two_proven_independent_third_parties_pass_skills_and_persist(session):
    first = third_party('e1', 'https://one.example/report', publisher='publisher-one', original='origin-one')
    second = third_party('e2', 'https://two.example/report', publisher='publisher-two', original='origin-two')
    skill_result, api_result = analysis_for([first, second], ['e1', 'e2'])
    assert len(skill_result.relations) == 1
    service = AnalysisPersistenceService(session)
    service.save(api_result)
    stored_first = EvidenceRepository(session).latest('e1')
    assert stored_first.independently_verified is True
    assert stored_first.normalized_source_host == 'one.example'
    assert stored_first.publisher_key == 'publisher-one'
    assert stored_first.original_source_key == 'origin-one'
    assert stored_first.independence_basis == 'publisher_and_original_source'
    assert service.get(api_result.analysis_id) == api_result


def test_same_host_is_not_two_independent_sources(session):
    evidence = [third_party('e1', 'https://www.same.example/a', publisher='one', original='origin-one'), third_party('e2', 'https://same.example/b', publisher='two', original='origin-two')]
    skill_result, api_result = analysis_for(evidence, ['e1', 'e2'])
    assert_direct_relation_rejected(session, skill_result, api_result, 'DIRECT_EVIDENCE_HOSTS_NOT_INDEPENDENT')


def test_distinct_values_across_three_records_do_not_replace_one_complete_pair(session):
    evidence = [
        third_party('e1', 'https://host-one.example/a', publisher='publisher-one', original='origin-one'),
        third_party('e2', 'https://host-one.example/b', publisher='publisher-two', original='origin-two'),
        third_party('e3', 'https://host-two.example/c', publisher='publisher-one', original='origin-two'),
    ]
    skill_result, api_result = analysis_for(evidence, ['e1', 'e2', 'e3'])
    assert_direct_relation_rejected(session, skill_result, api_result, 'DIRECT_EVIDENCE_PROVENANCE_NOT_INDEPENDENT')


def test_duplicate_evidence_id_is_not_counted_twice(session):
    evidence = [third_party('e1', 'https://one.example/a', publisher='one', original='origin-one')]
    skill_result, api_result = analysis_for(evidence, ['e1', 'e1'])
    assert_direct_relation_rejected(session, skill_result, api_result, 'DIRECT_EVIDENCE_INDEPENDENCE_METADATA_MISSING')


def test_missing_independence_metadata_is_rejected(session):
    evidence = [third_party('e1', 'https://one.example/a'), third_party('e2', 'https://two.example/b')]
    skill_result, api_result = analysis_for(evidence, ['e1', 'e2'])
    assert_direct_relation_rejected(session, skill_result, api_result, 'DIRECT_EVIDENCE_INDEPENDENCE_METADATA_MISSING')


def test_industry_model_cannot_be_promoted_by_skills_or_repository(session):
    evidence = [Evidence(id='industry', title='Synthetic industry model', source_url='https://model.example', published_at='2026-01-01', kind=EvidenceKind.industry_model, supports_claim=True, independently_verified=True)]
    skill_result, _ = analysis_for(evidence, ['industry'])
    assert skill_result.relations == []
