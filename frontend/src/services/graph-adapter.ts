import { MarkerType, type XYPosition } from "@xyflow/react";
import type { GraphAnalysisResponse } from "@/types/api";
import type { DominoEdge, DominoNode, DominoNodeKind, DominoRelationKind, GraphFixture } from "@/types/graph";

const captions: Record<DominoNodeKind, string> = { event: "事件", region: "地區", product: "產品", industry: "產業", company: "企業" };
const styles: Record<DominoRelationKind, { stroke: string; strokeDasharray?: string }> = {
  verified_direct: { stroke: "#1E293B" }, industry_inferred: { stroke: "#8B5CF6", strokeDasharray: "9 6" }, unverified_candidate: { stroke: "#64748B", strokeDasharray: "2 7" },
};
const columns: Record<DominoNodeKind, number> = { event: 20, region: 260, product: 260, industry: 540, company: 820 };
const rowStarts: Record<DominoNodeKind, number> = { event: 175, region: 30, product: 300, industry: 30, company: 30 };

export function responseToGraph(response: GraphAnalysisResponse): GraphFixture {
  const importantNodeIds = new Set(response.primary_paths.flatMap(path => path.node_ids));
  const evidence = new Map(response.evidence.map(item => [item.id, item]));
  const kindIndexes = new Map<DominoNodeKind, number>();
  const nodes: DominoNode[] = response.nodes.map(node => {
    const index = kindIndexes.get(node.kind) ?? 0;
    kindIndexes.set(node.kind, index + 1);
    const position: XYPosition = { x: columns[node.kind], y: rowStarts[node.kind] + index * 145 };
    return { id: node.id, type: node.kind, position, data: { kind: node.kind, label: node.label, caption: captions[node.kind], description: node.description, status: node.kind === "event" ? "情境起點" : node.kind === "company" ? "合成企業" : "合成節點", riskLabel: node.risk_label ?? undefined, fixtureRiskIndex: node.risk_index ?? undefined, onImportantPath: importantNodeIds.has(node.id) } };
  });
  const pathEdgePairs = new Set(response.primary_paths.flatMap(path => path.node_ids.slice(1).map((id, index) => `${path.node_ids[index]}:${id}`)));
  const edges: DominoEdge[] = response.edges.map(edge => {
    const important = pathEdgePairs.has(`${edge.source}:${edge.target}`);
    return { id: edge.id, source: edge.source, target: edge.target, label: edge.label, type: "smoothstep", className: important ? "important-flow-edge" : undefined, markerEnd: { type: MarkerType.ArrowClosed, color: styles[edge.kind].stroke }, style: { ...styles[edge.kind], strokeWidth: important ? 4 : 2.5 }, labelStyle: { fill: "#1E293B", fontWeight: 700, fontSize: 11 }, labelBgStyle: { fill: "#FFFDF5", fillOpacity: 0.96 }, labelBgPadding: [6, 4], labelBgBorderRadius: 6, data: { kind: edge.kind, relationLabel: edge.label, description: edge.description, evidenceStatus: edge.evidence_ids.length ? "附合成證據" : "無關聯證據", evidenceIds: edge.evidence_ids, evidenceSummaries: edge.evidence_ids.map(id => evidence.get(id)?.title).filter((title): title is string => Boolean(title)), includedInPropagation: edge.included_in_propagation, onImportantPath: important } };
  });
  const importantPath = response.primary_paths.reduce<string[]>((longest, path) => path.node_ids.length > longest.length ? path.node_ids : longest, []);
  return { mode: response.data_mode, title: response.scenario.description, nodes, edges, importantPath };
}
