from fastapi.testclient import TestClient

from app.api_adapter import adapt_analysis
from app.main import app
from app.schemas import AnalysisResult, Relation, RelationKind, Scenario

client = TestClient(app)


def demo_payload(**overrides):
    payload = {
        'description': '假設測試材料供應中斷 30 天',
        'event_type': 'supply_chain',
        'region': '虛構地區',
        'product': '測試材料',
        'duration_days': 30,
        'severity': 0.8,
        'seed_nodes': ['材料產業'],
    }
    payload.update(overrides)
    return payload


def test_health_contract():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'mode': 'synthetic_fixture'}


def test_demo_analysis_returns_graph_contract():
    response = client.post('/api/demo/analyze', json=demo_payload())
    assert response.status_code == 200
    body = response.json()
    assert body['analysis_id'].startswith('demo-')
    assert body['status'] == 'complete'
    assert body['data_mode'] == 'synthetic_fixture'
    assert body['scenario']['severity'] == 0.8
    assert body['nodes'] and body['edges'] and body['primary_paths']
    assert body['evidence'][0]['title'].startswith('合成示範資料')
    assert body['risk_results'][0]['risk_index'] == 80.0
    assert all(edge['kind'] == 'industry_inferred' for edge in body['edges'])
    assert all(edge['kind'] != 'verified_direct' for edge in body['edges'])


def test_unknown_severity_is_explicitly_insufficient():
    response = client.post('/api/demo/analyze', json=demo_payload(severity=None))
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'insufficient_evidence'
    assert body['risk_results'] == []
    assert body['primary_paths'] == []
    assert any(item['code'] == 'MISSING_SEVERITY' for item in body['findings'])


def test_candidate_relation_is_never_included_in_propagation():
    base = AnalysisResult(
        status='insufficient_evidence',
        scenario=Scenario(description='未知企業候選關係', severity=0.8, seed_nodes=['未知企業']),
        entities=['未知企業', '另一節點'],
        relations=[Relation(source='未知企業', target='另一節點', kind=RelationKind.candidate, weight=0.5)],
    )
    body = adapt_analysis(base)
    candidate = next(edge for edge in body.edges if edge.kind == 'unverified_candidate')
    assert candidate.included_in_propagation is False
    assert candidate.evidence_ids == []


def test_cors_allows_local_vite_origin_only():
    allowed = client.options('/api/demo/analyze', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'POST'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    denied = client.options('/api/demo/analyze', headers={'Origin': 'https://untrusted.example', 'Access-Control-Request-Method': 'POST'})
    assert 'access-control-allow-origin' not in denied.headers
