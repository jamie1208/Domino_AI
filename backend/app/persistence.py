"""Application-level persistence service; orchestration and Skills remain storage-agnostic."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories import AnalysisRepository, EvidenceRepository, GraphRepository
from app.schemas import GraphAnalysisResult

DATA_VERSION = 'synthetic-fixture-v1'


def _parse_date(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class AnalysisPersistenceService:
    def __init__(self, session: Session):
        self.session = session
        self.graph = GraphRepository(session)
        self.evidence = EvidenceRepository(session)
        self.analyses = AnalysisRepository(session)

    def save(self, result: GraphAnalysisResult) -> None:
        if self.analyses.get_result(result.analysis_id):
            return
        observed_at = _parse_date(result.analyzed_at)
        evidence_records = {}
        for item in result.evidence:
            source_url = None if result.data_mode == 'synthetic_fixture' else item.source_url
            record = self.evidence.create_version(
                evidence_id=item.id,
                title=item.title,
                content=item.quote_or_summary,
                kind=item.kind.value,
                verification_status='supported' if item.supports_claim else 'unverified',
                supports_claim=item.supports_claim,
                independently_verified=item.independently_verified,
                source_url=source_url,
                publisher_key=item.provenance.publisher_key,
                original_source_key=item.provenance.original_source_key,
                independence_basis=item.provenance.independence_basis,
                published_at=_parse_date(item.published_at),
                retrieved_at=observed_at,
                valid_from=observed_at,
                summary=item.quote_or_summary,
                metadata={'data_mode': result.data_mode, 'source_host_normalized': True},
            )
            evidence_records[item.id] = record.id

        node_records = {}
        for node in result.nodes:
            node_key = f'{result.data_mode}:{node.kind}:{node.label}' if node.kind != 'event' else f'{result.analysis_id}:{node.id}'
            latest = self.graph.latest_node(node_key)
            if latest and latest.kind == node.kind and latest.label == node.label:
                record = latest
            else:
                record = self.graph.create_node_version(node_key=node_key, kind=node.kind, label=node.label, valid_from=observed_at, data_version=DATA_VERSION, properties={'description': node.description, 'risk_label': node.risk_label})
            node_records[node.id] = record

        for edge in result.edges:
            edge_key = f'{result.analysis_id}:{edge.id}' if edge.id.startswith(('context-', 'seed-')) else f'{result.data_mode}:{edge.source}:{edge.target}:{edge.kind}'
            linked_evidence = [evidence_records[evidence_id] for evidence_id in edge.evidence_ids if evidence_id in evidence_records]
            latest = self.graph.latest_edge(edge_key)
            if latest and latest.relation_kind == edge.kind and latest.weight == edge.weight and latest.source_node_id == node_records[edge.source].id and latest.target_node_id == node_records[edge.target].id and latest.propagation_eligible == edge.included_in_propagation:
                continue
            self.graph.create_edge_version(edge_key=edge_key, source_node_id=node_records[edge.source].id, target_node_id=node_records[edge.target].id, relation_kind=edge.kind, weight=edge.weight, propagation_eligible=edge.included_in_propagation, valid_from=observed_at, data_version=DATA_VERSION, evidence_record_ids=linked_evidence, properties={'label': edge.label, 'description': edge.description})

        self.analyses.save(result, data_version=DATA_VERSION, parameters_snapshot={'scenario': result.scenario.model_dump(mode='json')})
        self.session.commit()

    def get(self, analysis_id: str) -> GraphAnalysisResult | None:
        return self.analyses.get_result(analysis_id)
