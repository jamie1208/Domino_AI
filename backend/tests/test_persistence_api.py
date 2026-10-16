from fastapi.testclient import TestClient

from app.database import engine_for_url
from app.main import app
from app.domain_errors import EvidenceAdmissionError

client = TestClient(app)


def test_saved_analysis_requires_database_configuration(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    response = client.get('/api/analyses/demo-missing')
    assert response.status_code == 503
    assert 'DATABASE_URL' in response.json()['detail']


def test_saved_analysis_reports_connection_failure(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://invalid:invalid@127.0.0.1:1/missing?connect_timeout=1')
    engine_for_url.cache_clear()
    response = client.get('/api/analyses/demo-missing')
    assert response.status_code == 503
    assert response.json()['detail'] == '資料庫連線失敗，無法讀取已保存分析。'
    engine_for_url.cache_clear()


def test_evidence_admission_failure_is_a_domain_422(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'sqlite+pysqlite:///:memory:')
    engine_for_url.cache_clear()
    monkeypatch.setattr('app.main.AnalysisPersistenceService.save', lambda self, response: (_ for _ in ()).throw(EvidenceAdmissionError('DIRECT_EVIDENCE_INSUFFICIENT', '證據不足')))
    response = client.post('/api/demo/analyze', json={'description': '合成准入錯誤測試', 'severity': .8, 'seed_nodes': ['材料產業']})
    assert response.status_code == 422
    assert response.json()['detail'] == {'code': 'DIRECT_EVIDENCE_INSUFFICIENT', 'message': '證據不足'}
    engine_for_url.cache_clear()
