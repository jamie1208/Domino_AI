import type { DominoNodeKind, DominoRelationKind } from "@/types/graph";

export interface ScenarioRequest {
  description: string;
  event_type: "natural_disaster" | "supply_chain" | "economic_policy" | "unknown";
  region: string | null;
  product: string | null;
  severity: number | null;
  duration_days: number | null;
  seed_nodes: string[];
}

export interface ApiGraphNode {
  id: string;
  kind: DominoNodeKind;
  label: string;
  description: string;
  risk_label: "高暴露" | "中度暴露" | "低度暴露" | null;
  risk_index: number | null;
}

export interface ApiGraphEdge {
  id: string;
  source: string;
  target: string;
  kind: DominoRelationKind;
  label: string;
  description: string;
  evidence_ids: string[];
  included_in_propagation: boolean;
  weight: number | null;
}

export interface ApiEvidence {
  id: string;
  title: string;
  source_url: string;
  published_at: string;
  kind: "official" | "third_party" | "industry_model" | "unverified";
  supports_claim: boolean;
  quote_or_summary: string;
  independently_verified: boolean;
}

export interface ApiRiskResult {
  node_id: string;
  relative_risk: number;
  risk_index: number;
  top_paths: string[][];
}

export interface GraphAnalysisResponse {
  analysis_id: string;
  scenario: ScenarioRequest;
  status: "complete" | "insufficient_evidence" | "invalid_input";
  data_mode: "synthetic_fixture" | "verified_public_data";
  model_version: string;
  analyzed_at: string;
  nodes: ApiGraphNode[];
  edges: ApiGraphEdge[];
  primary_paths: Array<{ id: string; node_ids: string[]; risk_index: number | null }>;
  evidence: ApiEvidence[];
  risk_results: ApiRiskResult[];
  limitations: string[];
  findings: Array<{ code: string; level: "info" | "warning" | "error"; message: string }>;
  explanation: string;
}
