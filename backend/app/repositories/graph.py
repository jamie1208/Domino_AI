from datetime import datetime

from sqlalchemy import or_, select

from app.db_models import EdgeEvidenceRecord, EvidenceRecord, GraphEdgeRecord, GraphNodeRecord
from app.domain_errors import InvalidGraphRelationshipError
from app.evidence_policy import admit_verified_direct
from app.repositories.base import Repository

class GraphRepository(Repository):
    def latest_node(self, node_key: str) -> GraphNodeRecord | None:
        return self.session.scalar(select(GraphNodeRecord).where(GraphNodeRecord.node_key == node_key).order_by(GraphNodeRecord.version.desc()).limit(1))

    def latest_edge(self, edge_key: str) -> GraphEdgeRecord | None:
        return self.session.scalar(select(GraphEdgeRecord).where(GraphEdgeRecord.edge_key == edge_key).order_by(GraphEdgeRecord.version.desc()).limit(1))

    def create_node_version(self, *, node_key: str, kind: str, label: str, valid_from: datetime, data_version: str, company_id: str | None = None, properties: dict | None = None) -> GraphNodeRecord:
        latest = self.latest_node(node_key)
        version = 1 if latest is None else latest.version + 1
        if latest and latest.valid_to is None:
            latest.valid_to = valid_from
        record = GraphNodeRecord(node_key=node_key, version=version, kind=kind, label=label, company_id=company_id, valid_from=valid_from, data_version=data_version, properties=properties or {})
        self.session.add(record)
        self.session.flush()
        self.log_change('graph_nodes', node_key, 'create' if version == 1 else 'supersede', version, {'id': record.id, 'kind': kind, 'label': label})
        return record

    def create_edge_version(self, *, edge_key: str, source_node_id: str, target_node_id: str, relation_kind: str, valid_from: datetime, data_version: str, weight: float | None = None, propagation_eligible: bool = False, evidence_record_ids: list[str] | None = None, properties: dict | None = None) -> GraphEdgeRecord:
        evidence_ids = evidence_record_ids or []
        if relation_kind == 'unverified_candidate' and propagation_eligible:
            raise InvalidGraphRelationshipError('未驗證候選關係不得參與風險傳播。')
        if relation_kind == 'verified_direct':
            records = list(self.session.scalars(select(EvidenceRecord).where(EvidenceRecord.id.in_(evidence_ids), EvidenceRecord.verification_status == 'supported', EvidenceRecord.supports_claim.is_(True)))) if evidence_ids else []
            admit_verified_direct(records)
        latest = self.latest_edge(edge_key)
        version = 1 if latest is None else latest.version + 1
        if latest and latest.valid_to is None:
            latest.valid_to = valid_from
        record = GraphEdgeRecord(edge_key=edge_key, version=version, source_node_id=source_node_id, target_node_id=target_node_id, relation_kind=relation_kind, weight=weight, propagation_eligible=propagation_eligible, valid_from=valid_from, data_version=data_version, properties=properties or {})
        self.session.add(record)
        self.session.flush()
        for evidence_id in evidence_ids:
            self.session.add(EdgeEvidenceRecord(edge_id=record.id, evidence_record_id=evidence_id))
        self.log_change('graph_edges', edge_key, 'create' if version == 1 else 'supersede', version, {'id': record.id, 'kind': relation_kind, 'propagation_eligible': propagation_eligible})
        return record

    def nodes_at(self, as_of: datetime) -> list[GraphNodeRecord]:
        return list(self.session.scalars(select(GraphNodeRecord).where(GraphNodeRecord.valid_from <= as_of, or_(GraphNodeRecord.valid_to.is_(None), GraphNodeRecord.valid_to > as_of))))

    def edges_at(self, as_of: datetime, propagation_only: bool = False) -> list[GraphEdgeRecord]:
        statement = select(GraphEdgeRecord).where(GraphEdgeRecord.valid_from <= as_of, or_(GraphEdgeRecord.valid_to.is_(None), GraphEdgeRecord.valid_to > as_of))
        if propagation_only:
            statement = statement.where(GraphEdgeRecord.propagation_eligible.is_(True), GraphEdgeRecord.relation_kind != 'unverified_candidate')
        return list(self.session.scalars(statement))

    def node_history(self, node_key: str) -> list[GraphNodeRecord]:
        return list(self.session.scalars(select(GraphNodeRecord).where(GraphNodeRecord.node_key == node_key).order_by(GraphNodeRecord.version)))

    def edge_history(self, edge_key: str) -> list[GraphEdgeRecord]:
        return list(self.session.scalars(select(GraphEdgeRecord).where(GraphEdgeRecord.edge_key == edge_key).order_by(GraphEdgeRecord.version)))
