import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CircleAlert, Route } from "lucide-react";
import { useLocation } from "react-router-dom";
import { AnalysisGraph } from "@/components/graph/analysis-graph";
import { PageHeading } from "@/components/page-heading";
import { SyntheticBadge } from "@/components/synthetic-badge";
import { Card } from "@/components/ui/card";
import { analyzeScenario, DEFAULT_DEMO_SCENARIO } from "@/services/analysis-api";
import { responseToGraph } from "@/services/graph-adapter";
import type { GraphAnalysisResponse, ScenarioRequest } from "@/types/api";
import type { GraphFixture, GraphViewState } from "@/types/graph";

const emptyGraph: GraphFixture = { mode: "synthetic_fixture", title: "分析準備中", nodes: [], edges: [], importantPath: [] };

export function AnalysisPage() {
  const location = useLocation();
  const submitted = (location.state as { scenario?: ScenarioRequest } | null)?.scenario;
  const scenario = useMemo(() => submitted ?? DEFAULT_DEMO_SCENARIO, [submitted]);
  const [response, setResponse] = useState<GraphAnalysisResponse | null>(null);
  const [viewState, setViewState] = useState<GraphViewState>("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setViewState("loading"); setError(""); setResponse(null);
    analyzeScenario(scenario, controller.signal).then(result => {
      setResponse(result);
      setViewState(result.nodes.length === 0 ? "empty" : "ready");
    }).catch(reason => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "分析服務發生未知錯誤。");
      setViewState("error");
    });
    return () => controller.abort();
  }, [scenario, attempt]);

  const graph = useMemo(() => response ? responseToGraph(response) : emptyGraph, [response]);
  const importantLabels = graph.importantPath.map(id => graph.nodes.find(node => node.id === id)?.data.label).filter((label): label is string => Boolean(label));
  const title = response?.scenario.description ?? scenario.description;

  return <section className="page-container py-12 sm:py-16">
    <PageHeading eyebrow="API Analysis" title={title} description="分析結果由 FastAPI、現有 Skills Orchestrator 與 Python deterministic risk engine 產生；前端只負責呈現。" aside={<SyntheticBadge />} />
    {response && <div className="mt-8 grid gap-6 md:grid-cols-3"><Metric label="分析狀態" value={response.status === "complete" ? "完成" : response.status === "invalid_input" ? "輸入無效" : "證據不足"} note={`模型 ${response.model_version}`} /><Metric label="圖譜規模" value={`${response.nodes.length} / ${response.edges.length}`} note="節點／關係" /><Metric label="資料模式" value="FIXTURE" note={new Date(response.analyzed_at).toLocaleString("zh-TW")} /></div>}
    <div className="mt-8"><AnalysisGraph fixture={graph} state={viewState} errorMessage={error} onRetry={() => setAttempt(value => value + 1)} /></div>
    {response && viewState === "ready" && <div className="mt-8 grid gap-8 lg:grid-cols-12">
      <Card className="p-6 shadow-yellow lg:col-span-8 sm:p-7"><div className="flex items-center gap-3"><span className="grid size-11 place-items-center rounded-full border-2 border-foreground bg-tertiary"><Route size={21} /></span><div><p className="text-xs font-extrabold uppercase tracking-widest text-muted-foreground">Primary Path</p><h2 className="text-2xl">主要風險傳播路徑</h2></div></div>{importantLabels.length ? <ol className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-label="主要風險傳播路徑">{importantLabels.map((label, index) => <li key={`${label}-${index}`} className="relative flex min-h-20 items-center gap-3 rounded-md border-2 border-foreground bg-white p-3 text-sm font-bold"><span className="grid size-7 shrink-0 place-items-center rounded-full border-2 border-foreground bg-secondary text-xs">{index + 1}</span><span className="break-words">{label}</span>{index < importantLabels.length - 1 && <ArrowRight className="absolute -right-5 top-1/2 z-10 hidden -translate-y-1/2 xl:block" size={18} aria-hidden />}</li>)}</ol> : <p className="mt-6 text-sm text-muted-foreground">目前沒有可顯示的主要路徑。</p>}<p className="mt-5 rounded-md border-2 border-dashed border-foreground bg-muted p-4 text-sm leading-6 text-muted-foreground">{response.explanation || "沒有具足夠證據的風險說明。"}</p></Card>
      <div className="space-y-6 lg:col-span-4"><Card className="p-6"><h2 className="text-xl">Python 風險結果</h2>{response.risk_results.length ? <div className="mt-5 space-y-3">{response.risk_results.map((risk, index) => <div key={risk.node_id} className="flex min-h-16 items-center gap-3 rounded-md border-2 border-foreground p-3"><span className="grid size-9 shrink-0 place-items-center rounded-full border-2 border-foreground bg-secondary text-sm font-extrabold">{index + 1}</span><span className="min-w-0 flex-1"><strong className="block truncate text-sm">{risk.node_id}</strong><span className="text-xs text-muted-foreground">合成相對索引 {risk.risk_index}</span></span></div>)}</div> : <p className="mt-4 text-sm text-muted-foreground">缺少已確認強度或起始節點，因此 Python 未產生索引。</p>}</Card><Card className="border-dashed bg-muted p-5"><CircleAlert size={22} /><h3 className="mt-3 text-lg">限制與驗證訊息</h3><ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">{response.limitations.map(item => <li key={item}>• {item}</li>)}</ul></Card></div>
    </div>}
  </section>;
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) { return <Card className="p-5 shadow-hard"><p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</p><p className="mt-2 font-heading text-2xl font-extrabold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{note}</p></Card>; }
