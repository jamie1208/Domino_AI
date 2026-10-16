from fastapi.testclient import TestClient

from app.database import engine_for_url
from app.main import app

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
