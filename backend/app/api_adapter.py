"""Adapt the existing orchestrator result to the frontend graph contract."""
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import (
    AnalysisResult,
    GraphAnalysisResult,
    GraphEdge,
    GraphNode,
    PrimaryPath,
    RelationKind,
)

RELATION_KIND = {
    RelationKind.verified_direct: 'verified_direct',
    RelationKind.corroborated_direct: 'verified_direct',
    RelationKind.industry_dependency: 'industry_inferred',
    RelationKind.shared_exposure: 'industry_inferred',
    RelationKind.candidate: 'unverified_candidate',
}

RELATION_LABEL = {
    'verified_direct': '已驗證直接關係',
    'industry_inferred': '產業推論',
    'unverified_candidate': '未驗證候選',
}


def _risk_label(risk_index: float | None) -> str | None:
    if risk_index is None:
        return None
    if risk_index >= 70:
        return '高暴露'
    if risk_index >= 40:
        return '中度暴露'
    return '低度暴露'


def adapt_analysis(result: AnalysisResult) -> GraphAnalysisResult:
    """Pure presentation adapter; it never calculates or changes risk values."""
    scenario = result.scenario
    entity_ids = {name: f'entity-{index + 1}' for index, name in enumerate(result.entities)}
    risk_by_node = {risk.node_id: risk.risk_index for risk in result.companies}
    nodes = [
        GraphNode(
            id='event-1',
            kind='event',
            label=scenario.description,
            description='使用者提交的示範危機情境。',
        )
    ]
    if scenario.region:
        nodes.append(GraphNode(id='region-1', kind='region', label=scenario.region, description='情境指定地區；未宣稱為真實事件。'))
    if scenario.product:
        nodes.append(GraphNode(id='product-1', kind='product', label=scenario.product, description='情境指定產品；未宣稱為真實事件。'))
    nodes.extend(
        GraphNode(
            id=entity_ids[name],
            kind='industry',
            label=name,
            description='合成 fixture 中的產業節點，不代表真實企業關係。',
            risk_label=_risk_label(risk_by_node.get(name)),
            risk_index=risk_by_node.get(name),
        )
        for name in result.entities
    )

    edges: list[GraphEdge] = []
    if scenario.region:
        edges.append(GraphEdge(id='context-region', source='event-1', target='region-1', kind='industry_inferred', label='情境地區', description='使用者輸入的情境條件，不是供應鏈證據。', included_in_propagation=False))
    if scenario.product:
        edges.append(GraphEdge(id='context-product', source='event-1', target='product-1', kind='industry_inferred', label='影響產品', description='使用者輸入的情境條件，不是供應鏈證據。', included_in_propagation=False))
    for index, seed in enumerate(scenario.seed_nodes):
        if seed in entity_ids:
            edges.append(GraphEdge(id=f'seed-{index + 1}', source='event-1', target=entity_ids[seed], kind='industry_inferred', label='起始暴露', description='使用者指定的風險傳播起點。', included_in_propagation=True))
    for index, relation in enumerate(result.relations):
        kind = RELATION_KIND[relation.kind]
        edges.append(GraphEdge(
            id=f'relation-{index + 1}',
            source=entity_ids[relation.source],
            target=entity_ids[relation.target],
            kind=kind,
            label=RELATION_LABEL[kind],
            description='由現有 Skills 驗證流程接受的合成關係。' if kind != 'unverified_candidate' else '候選關係未通過驗證，不納入傳播。',
            evidence_ids=relation.evidence_ids,
            included_in_propagation=kind != 'unverified_candidate',
            weight=relation.weight,
        ))

    primary_paths = [
        PrimaryPath(
            id=f'path-{company_index + 1}-{path_index + 1}',
            node_ids=['event-1', *[entity_ids[name] for name in path if name in entity_ids]],
            risk_index=company.risk_index,
        )
        for company_index, company in enumerate(result.companies)
        for path_index, path in enumerate(company.top_paths)
    ]
    limitations = [result.disclaimer, '目前僅使用合成 fixture；不得解讀為真實企業分析。']
    limitations.extend(finding.message for finding in result.findings)
    return GraphAnalysisResult(
        analysis_id=f'demo-{uuid4()}',
        scenario=scenario,
        status=result.status,
        data_mode='synthetic_fixture',
        model_version=result.model_version,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        nodes=nodes,
        edges=edges,
        primary_paths=primary_paths,
        evidence=result.evidence,
        risk_results=result.companies,
        limitations=list(dict.fromkeys(limitations)),
        findings=result.findings,
        explanation=result.explanation,
    )
