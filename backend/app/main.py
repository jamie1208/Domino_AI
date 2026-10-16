import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.schemas import Scenario, GraphAnalysisResult
from app.orchestrator import Orchestrator
from app.fixture import FixtureProvider
from app.api_adapter import adapt_analysis
from app.database import DatabaseNotConfiguredError, database_url, session_factory
from app.persistence import AnalysisPersistenceService

app=FastAPI(title='Domino AI MVP — synthetic demonstration',version='0.1.0')

allowed_origins = [
    origin.strip()
    for origin in os.getenv('DOMINO_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'OPTIONS'],
    allow_headers=['Content-Type'],
)

@app.get('/api/health')
def health(): return {'status':'ok','mode':'synthetic_fixture'}

@app.post('/api/demo/analyze',response_model=GraphAnalysisResult)
def demo_analyze(scenario:Scenario):
    """Explicit DEMO endpoint. Only synthetic edges and synthetic evidence."""
    result = Orchestrator(FixtureProvider()).run(scenario,data_mode='fixture')
    response = adapt_analysis(result)
    if os.getenv('DATABASE_URL', '').strip():
        try:
            with session_factory()() as session:
                AnalysisPersistenceService(session).save(response)
        except (SQLAlchemyError, OSError) as exc:
            raise HTTPException(status_code=503, detail='分析已完成，但資料庫持久化失敗；未回傳假的保存結果。') from exc
    return response

@app.get('/api/analyses/{analysis_id}',response_model=GraphAnalysisResult)
def get_saved_analysis(analysis_id: str):
    """Return a stored immutable response snapshot without rerunning risk calculation."""
    try:
        database_url()
        with session_factory()() as session:
            result = AnalysisPersistenceService(session).get(analysis_id)
    except DatabaseNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(status_code=503, detail='資料庫連線失敗，無法讀取已保存分析。') from exc
    if result is None:
        raise HTTPException(status_code=404, detail='找不到指定的分析結果。')
    return result
