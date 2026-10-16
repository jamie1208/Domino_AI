import type { GraphAnalysisResponse, ScenarioRequest } from "@/types/api";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export const DEFAULT_DEMO_SCENARIO: ScenarioRequest = {
  description: "假設測試材料供應中斷 30 天",
  event_type: "supply_chain",
  region: "虛構地區",
  product: "測試材料",
  duration_days: 30,
  severity: 0.8,
  seed_nodes: ["材料產業"],
};

export class AnalysisApiError extends Error {
  constructor(message: string, public readonly status?: number) { super(message); this.name = "AnalysisApiError"; }
}

export async function analyzeScenario(scenario: ScenarioRequest, signal?: AbortSignal): Promise<GraphAnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/demo/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scenario),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new AnalysisApiError("無法連線至分析服務，請確認 FastAPI 已啟動。", undefined);
  }
  if (!response.ok) {
    let detail = "分析服務回傳錯誤。";
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map(item => item.msg).filter(Boolean).join("；") || detail;
    } catch { /* keep the safe fallback message */ }
    throw new AnalysisApiError(detail, response.status);
  }
  return response.json() as Promise<GraphAnalysisResponse>;
}
