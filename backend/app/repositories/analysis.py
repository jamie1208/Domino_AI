from datetime import datetime
from hashlib import sha256
import json

from sqlalchemy import select

from app.db_models import AnalysisRecord, AnalysisResultRecord, ScenarioRecord
from app.repositories.base import Repository
from app.schemas import GraphAnalysisResult


class AnalysisRepository(Repository):
    def save(self, result: GraphAnalysisResult, *, data_version: str, parameters_snapshot: dict) -> AnalysisRecord:
        existing = self.session.get(AnalysisRecord, result.analysis_id)
        if existing:
            return existing
        scenario_payload = result.scenario.model_dump(mode='json')
        input_hash = sha256(json.dumps(scenario_payload, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
        scenario = ScenarioRecord(input_hash=input_hash, input_snapshot=scenario_payload)
        self.session.add(scenario)
        self.session.flush()
        analysis = AnalysisRecord(id=result.analysis_id, scenario_id=scenario.id, status=result.status, data_mode=result.data_mode, model_version=result.model_version, data_version=data_version, parameters_snapshot=parameters_snapshot, analyzed_at=datetime.fromisoformat(result.analyzed_at))
        self.session.add(analysis)
        self.session.flush()
        risk_values = [item.risk_index for item in result.risk_results if item.risk_index is not None]
        self.session.add(AnalysisResultRecord(analysis_id=analysis.id, result_payload=result.model_dump(mode='json'), risk_index=max(risk_values) if risk_values else None))
        self.log_change('analyses', analysis.id, 'snapshot', 1, {'status': analysis.status, 'model_version': analysis.model_version, 'data_version': data_version})
        return analysis

    def get_result(self, analysis_id: str) -> GraphAnalysisResult | None:
        record = self.session.scalar(select(AnalysisResultRecord).where(AnalysisResultRecord.analysis_id == analysis_id))
        return GraphAnalysisResult.model_validate(record.result_payload) if record else None
