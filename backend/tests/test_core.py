from app.schemas import Scenario, Evidence, EvidenceKind, Relation, RelationKind
from app.skills.event_parser import EventParserSkill
from app.skills.evidence_verifier import EvidenceVerifierSkill
from app.skills.researcher import ResearchBundle
from app.fixture import FixtureProvider
from app.orchestrator import Orchestrator

def test_parser_does_not_invent_severity():
    s=EventParserSkill().run(Scenario(description='日本地震，供應中斷30天'))
    assert s.event_type == 'natural_disaster'
    assert s.duration_days == 30
    assert s.severity is None

def test_demo_propagation():
    r=Orchestrator(FixtureProvider()).run(Scenario(description='測試材料短缺情境',severity=.8,seed_nodes=['材料產業']))
    assert r.status == 'complete'
    scores={x.node_id:x.relative_risk for x in r.companies}
    assert scores['材料產業']==.8
    assert scores['晶圓製造']==.56
    assert scores['電子製造']==.336
    assert r.data_mode == 'fixture'

def test_unknown_severity_does_not_issue_score():
    r=Orchestrator(FixtureProvider()).run(Scenario(description='測試材料短缺情境',seed_nodes=['材料產業']))
    assert r.status == 'insufficient_evidence'
    assert not r.companies

def test_unsubstantiated_direct_claim_rejected():
    ev=Evidence(id='1',title='模糊報導',source_url='https://example.org/demo',published_at='2026-01-01',kind=EvidenceKind.third_party,supports_claim=False)
    rel=Relation(source='A',target='B',kind=RelationKind.verified_direct,weight=.5,evidence_ids=['1'])
    accepted,findings=EvidenceVerifierSkill().run(ResearchBundle([ev],[rel]))
    assert not accepted
    assert any(f.code == 'UNSUPPORTED_CLAIM' for f in findings)

def test_industry_relation_is_not_direct_supplier_relation():
    r=Orchestrator(FixtureProvider()).run(Scenario(description='測試材料短缺情境',severity=.8,seed_nodes=['材料產業']))
    assert all(rel.kind == RelationKind.industry_dependency for rel in r.relations)
