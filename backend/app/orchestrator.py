"""Fixed-stage orchestration (F37); demo local provider never queries internet."""
from app.schemas import AnalysisResult, Scenario, ValidationFinding
from app.skills.event_parser import EventParserSkill
from app.skills.researcher import ResearchSkill, EmptyPublicDataProvider
from app.skills.evidence_verifier import EvidenceVerifierSkill
from app.skills.knowledge_graph import KnowledgeGraphSkill
from app.skills.explainer import ExplainerSkill
from app.risk_engine.network import calculate

class Orchestrator:
    def __init__(self, provider=None):
        self.parser=EventParserSkill()
        self.research=ResearchSkill(provider or EmptyPublicDataProvider())
        self.verify=EvidenceVerifierSkill()
        self.graph=KnowledgeGraphSkill()
        self.explain=ExplainerSkill()

    def run(self,scenario:Scenario,data_mode='fixture') -> AnalysisResult:
        scenario=self.parser.run(scenario)
        bundle=self.research.run(scenario)
        relations,findings=self.verify.run(bundle)
        graph=self.graph.run(relations)
        if scenario.severity is None:
            findings.append(ValidationFinding(code='MISSING_SEVERITY',level='warning',message='事件強度未確認，不可自行推定'))
        if not scenario.seed_nodes:
            findings.append(ValidationFinding(code='MISSING_SEEDS',level='warning',message='尚未確認起始暴露節點'))
        companies=calculate(graph,scenario.seed_nodes,scenario.severity)
        status='complete' if companies else 'insufficient_evidence'
        return AnalysisResult(status=status,scenario=scenario,entities=sorted(graph.nodes),relations=relations,evidence=bundle.evidence,companies=companies,findings=findings,explanation=self.explain.run(scenario,companies,findings),data_mode=data_mode)
