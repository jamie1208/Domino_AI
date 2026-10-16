"""All demo data is synthetic. DO NOT relabel this as verified public data."""
from app.schemas import Evidence, EvidenceKind, Relation, RelationKind
from app.skills.researcher import ResearchBundle

class FixtureProvider:
    def retrieve(self,scenario):
        evidence=[Evidence(id='demo-e1',title='合成示範資料（非真實公開來源）',source_url='https://example.org/demo-only',published_at='2026-01-01',kind=EvidenceKind.industry_model,supports_claim=True,quote_or_summary='純示範：虛構的產業依賴網絡')]
        relations=[Relation(source='材料產業',target='晶圓製造',kind=RelationKind.industry_dependency,weight=.7,evidence_ids=['demo-e1']),Relation(source='晶圓製造',target='電子製造',kind=RelationKind.industry_dependency,weight=.6,evidence_ids=['demo-e1']),Relation(source='電子製造',target='物流服務',kind=RelationKind.industry_dependency,weight=.3,evidence_ids=['demo-e1'])]
        return ResearchBundle(evidence=evidence,candidate_relations=relations)
