import { MarkerType, type XYPosition } from "@xyflow/react";
import type { DominoEdge, DominoNode, DominoNodeData, DominoNodeKind, DominoRelationKind, GraphFixture } from "@/types/graph";

const position = (x: number, y: number): XYPosition => ({ x, y });
type NodeFixtureInput = Pick<DominoNodeData, "label" | "caption" | "description" | "status" | "riskLabel" | "fixtureRiskIndex" | "onImportantPath">;
const node = (id: string, kind: DominoNodeKind, at: XYPosition, data: NodeFixtureInput): DominoNode => ({ id, type: kind, position: at, data: { kind, ...data } });

const relationAppearance: Record<DominoRelationKind, { stroke: string; strokeDasharray?: string }> = {
  verified_direct: { stroke: "#1E293B" },
  industry_inferred: { stroke: "#8B5CF6", strokeDasharray: "9 6" },
  unverified_candidate: { stroke: "#64748B", strokeDasharray: "2 7" },
};

function edge(id: string, source: string, target: string, kind: DominoRelationKind, label: string, important = false): DominoEdge {
  const included = kind !== "unverified_candidate";
  return {
    id, source, target, label, type: "smoothstep", markerEnd: { type: MarkerType.ArrowClosed, color: relationAppearance[kind].stroke },
    className: important ? "important-flow-edge" : undefined,
    style: { ...relationAppearance[kind], strokeWidth: important ? 4 : 2.5 },
    labelStyle: { fill: "#1E293B", fontWeight: 700, fontSize: 11 }, labelBgStyle: { fill: "#FFFDF5", fillOpacity: 0.96 }, labelBgPadding: [6, 4], labelBgBorderRadius: 6,
    data: { kind, relationLabel: label, description: relationDescriptions[kind], evidenceStatus: relationEvidence[kind], evidenceIds: [], includedInPropagation: included, onImportantPath: important },
  };
}

const relationDescriptions: Record<DominoRelationKind, string> = {
  verified_direct: "合成範例中的直接關係。正式資料必須通過明確證據驗證。",
  industry_inferred: "依產業結構建立的推論關係，與企業直接關係分開呈現。",
  unverified_candidate: "僅供檢視的候選關係，未納入風險傳播。",
};
const relationEvidence: Record<DominoRelationKind, string> = { verified_direct: "合成直接關係", industry_inferred: "產業推論", unverified_candidate: "未驗證候選" };

export const graphFixture: GraphFixture = {
  mode: "synthetic_fixture",
  title: "測試材料供應中斷 30 天",
  importantPath: ["event-1", "region-1", "product-1", "industry-1", "company-a"],
  nodes: [
    node("event-1", "event", position(20, 155), { label: "供應中斷", caption: "事件", description: "假設測試材料供應中斷 30 天。", status: "情境起點", onImportantPath: true }),
    node("region-1", "region", position(260, 40), { label: "虛構地區", caption: "地區", description: "僅供介面展示的虛構事件地區。", status: "合成節點", onImportantPath: true }),
    node("product-1", "product", position(260, 270), { label: "測試材料", caption: "產品", description: "合成情境中的測試材料品項。", status: "合成節點", onImportantPath: true }),
    node("industry-1", "industry", position(520, 155), { label: "測試零組件業", caption: "產業", description: "合成產業節點，不代表真實產業依賴。", status: "合成節點", onImportantPath: true }),
    node("company-a", "company", position(800, 35), { label: "範例元件 A", caption: "企業", description: "虛構企業，用於測試企業節點資訊。", status: "合成企業", riskLabel: "高暴露", fixtureRiskIndex: 78, onImportantPath: true }),
    node("company-b", "company", position(800, 175), { label: "範例製造 B", caption: "企業", description: "虛構企業，用於測試產業推論關係。", status: "合成企業", riskLabel: "中度暴露", fixtureRiskIndex: 61 }),
    node("company-c", "company", position(800, 315), { label: "範例通路 C", caption: "企業", description: "虛構企業，僅具有未驗證候選關係。", status: "合成企業", riskLabel: "低度暴露", fixtureRiskIndex: 34 }),
  ],
  edges: [
    edge("e-event-region", "event-1", "region-1", "verified_direct", "發生於", true),
    edge("e-event-product", "event-1", "product-1", "verified_direct", "影響品項", true),
    edge("e-region-industry", "region-1", "industry-1", "industry_inferred", "區域暴露", true),
    edge("e-product-industry", "product-1", "industry-1", "verified_direct", "材料依賴", true),
    edge("e-industry-a", "industry-1", "company-a", "verified_direct", "合成直接關係", true),
    edge("e-industry-b", "industry-1", "company-b", "industry_inferred", "產業推論"),
    edge("e-industry-c", "industry-1", "company-c", "unverified_candidate", "未驗證候選"),
  ],
};
