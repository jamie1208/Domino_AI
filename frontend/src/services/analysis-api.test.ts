import { afterEach, describe, expect, it, vi } from "vitest";
import { analyzeScenario, AnalysisApiError, DEFAULT_DEMO_SCENARIO } from "@/services/analysis-api";

afterEach(() => vi.unstubAllGlobals());

describe("analyzeScenario", () => {
  it("rejects a failed API request instead of returning fixture data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "服務暫停" }), { status: 503, headers: { "Content-Type": "application/json" } })));
    await expect(analyzeScenario(DEFAULT_DEMO_SCENARIO)).rejects.toEqual(expect.objectContaining<Partial<AnalysisApiError>>({ name: "AnalysisApiError", message: "服務暫停", status: 503 }));
  });
});
