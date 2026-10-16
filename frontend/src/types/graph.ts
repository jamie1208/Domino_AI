import type { Edge, Node } from "@xyflow/react";

export type DominoNodeKind = "event" | "region" | "product" | "industry" | "company";
export type DominoRelationKind = "verified_direct" | "industry_inferred" | "unverified_candidate";

export interface DominoNodeData extends Record<string, unknown> {
  kind: DominoNodeKind;
  label: string;
  caption: string;
  description: string;
  status: "情境起點" | "合成節點" | "合成企業";
  riskLabel?: "高暴露" | "中度暴露" | "低度暴露";
  fixtureRiskIndex?: number;
  onImportantPath?: boolean;
}

export interface DominoEdgeData extends Record<string, unknown> {
  kind: DominoRelationKind;
  relationLabel: string;
  description: string;
  evidenceStatus: string;
  evidenceIds: readonly string[];
  evidenceSummaries?: readonly string[];
  includedInPropagation: boolean;
  onImportantPath?: boolean;
}

export type DominoNode = Node<DominoNodeData, DominoNodeKind>;
export type DominoEdge = Edge<DominoEdgeData>;

export interface GraphFixture {
  mode: "synthetic_fixture" | "verified_public_data";
  title: string;
  nodes: DominoNode[];
  edges: DominoEdge[];
  importantPath: readonly string[];
}

export type GraphSelection =
  | { type: "node"; item: DominoNode }
  | { type: "edge"; item: DominoEdge }
  | null;

export type GraphViewState = "ready" | "loading" | "empty" | "error";
