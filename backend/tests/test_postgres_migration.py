import os
import subprocess

import pytest
from sqlalchemy import create_engine, inspect, text
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.database import engine_for_url
from app.main import app


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL is required for PostgreSQL migration integration test')
def test_postgres_migration_is_repeatable_and_complete():
    url = os.environ['TEST_DATABASE_URL']
    env = {**os.environ, 'DATABASE_URL': url}
    subprocess.run(['.venv/bin/alembic', 'upgrade', 'head'], check=True, env=env)
    subprocess.run(['.venv/bin/alembic', 'upgrade', 'head'], check=True, env=env)
    engine = create_engine(url)
    expected = {'companies', 'graph_nodes', 'graph_edges', 'evidence', 'edge_evidence', 'scenarios', 'analyses', 'analysis_results', 'data_change_log', 'alembic_version'}
    assert expected <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.scalar(text('select count(*) from alembic_version')) == 1


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL is required for PostgreSQL persistence integration test')
def test_postgres_analysis_save_and_read_does_not_recalculate(monkeypatch):
    url = os.environ['TEST_DATABASE_URL']
    monkeypatch.setenv('DATABASE_URL', url)
    engine_for_url.cache_clear()
    client = TestClient(app)
    payload = {'description': 'PostgreSQL 合成整合測試', 'event_type': 'supply_chain', 'region': '虛構地區', 'product': '測試材料', 'duration_days': 30, 'severity': 0.8, 'seed_nodes': ['材料產業']}
    created = client.post('/api/demo/analyze', json=payload)
    assert created.status_code == 200
    analysis_id = created.json()['analysis_id']
    with patch('app.main.Orchestrator.run', side_effect=AssertionError('GET must not recalculate')):
        loaded = client.get(f'/api/analyses/{analysis_id}')
    assert loaded.status_code == 200
    assert loaded.json() == created.json()
    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.scalar(text('select count(*) from graph_nodes')) > 0
        assert connection.scalar(text('select count(*) from graph_edges')) > 0
        assert connection.scalar(text('select count(*) from evidence')) > 0
