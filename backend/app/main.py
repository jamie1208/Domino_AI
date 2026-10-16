import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import Scenario, GraphAnalysisResult
from app.orchestrator import Orchestrator
from app.fixture import FixtureProvider
from app.api_adapter import adapt_analysis

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
    return adapt_analysis(result)
