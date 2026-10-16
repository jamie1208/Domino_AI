import { describe, expect, it } from "vitest";
import { responseToGraph } from "@/services/graph-adapter";
import type { GraphAnalysisResponse } from "@/types/api";

const response: GraphAnalysisResponse = {
  analysis_id: "demo-test", status: "complete", data_mode: "synthetic_fixture", model_version: "demo-0.1", analyzed_at: "2026-01-01T00:00:00Z",
  scenario: { description: "測試中斷", event_type: "supply_chain", region: null, product: null, severity: 0.8, duration_days: 30, seed_nodes: ["材料產業"] },
  nodes: [{ id: "event-1", kind: "event", label: "測試中斷", description: "測試", risk_label: null, risk_index: null }, { id: "entity-1", kind: "industry", label: "材料產業", description: "測試", risk_label: "高暴露", risk_index: 80 }],
  edges: [{ id: "seed-1", source: "event-1", target: "entity-1", kind: "industry_inferred", label: "起始暴露", description: "測試", evidence_ids: [], included_in_propagation: true, weight: null }],
  primary_paths: [{ id: "path-1", node_ids: ["event-1"], risk_index: 80 }, { id: "path-2", node_ids: ["event-1", "entity-1"], risk_index: 80 }], evidence: [], risk_results: [{ node_id: "材料產業", relative_risk: 0.8, risk_index: 80, top_paths: [["材料產業"]] }], limitations: [], findings: [], explanation: "合成測試",
};

describe("responseToGraph", () => {
  it("preserves API nodes, edges and primary path without calculating risk", () => {
    const graph = responseToGraph(response);
    expect(graph.nodes).toHaveLength(2);
    expect(graph.edges).toHaveLength(1);
    expect(graph.importantPath).toEqual(["event-1", "entity-1"]);
    expect(graph.nodes[1].data.fixtureRiskIndex).toBe(80);
    expect(graph.edges[0].data?.kind).toBe("industry_inferred");
  });
});
