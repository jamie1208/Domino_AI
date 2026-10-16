from fastapi import FastAPI
from app.schemas import Scenario, AnalysisResult
from app.orchestrator import Orchestrator
from app.fixture import FixtureProvider

app=FastAPI(title='Domino AI MVP — synthetic demonstration',version='0.1.0')

@app.get('/api/health')
def health(): return {'status':'ok','mode':'synthetic_fixture'}

@app.post('/api/demo/analyze',response_model=AnalysisResult)
def demo_analyze(scenario:Scenario):
    """Explicit DEMO endpoint. Only synthetic edges and synthetic evidence."""
    return Orchestrator(FixtureProvider()).run(scenario,data_mode='fixture')
