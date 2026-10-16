"""Idempotent, explicitly synthetic Phase 4 development seed."""
from app.api_adapter import adapt_analysis
from app.database import session_factory
from app.fixture import FixtureProvider
from app.orchestrator import Orchestrator
from app.persistence import AnalysisPersistenceService
from app.schemas import Scenario


def main() -> None:
    scenario = Scenario(description='Phase 4 合成資料庫種子', event_type='supply_chain', region='虛構地區', product='測試材料', duration_days=30, severity=.8, seed_nodes=['材料產業'])
    response = adapt_analysis(Orchestrator(FixtureProvider()).run(scenario, data_mode='fixture'))
    response.analysis_id = 'demo-seed-phase4-v1'
    response.analyzed_at = '2026-01-01T00:00:00+00:00'
    with session_factory()() as session:
        AnalysisPersistenceService(session).save(response)
    print('Synthetic seed ready: demo-seed-phase4-v1')


if __name__ == '__main__':
    main()
