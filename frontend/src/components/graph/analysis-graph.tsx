import { useCallback, useMemo, useState } from "react";
import { AlertTriangle, LoaderCircle, SearchX } from "lucide-react";
import { Background, BackgroundVariant, Controls, MiniMap, ReactFlow, type NodeTypes } from "@xyflow/react";
import { DominoNodeView } from "@/components/graph/domino-node";
import { SelectionPanel } from "@/components/graph/selection-panel";
import { Button } from "@/components/ui/button";
import type { GraphFixture, GraphSelection, GraphViewState } from "@/types/graph";

const nodeTypes: NodeTypes = { event: DominoNodeView, region: DominoNodeView, product: DominoNodeView, industry: DominoNodeView, company: DominoNodeView };

export function AnalysisGraph({ fixture, state = "ready", errorMessage, onRetry }: { fixture: GraphFixture; state?: GraphViewState; errorMessage?: string; onRetry?: () => void }) {
  const [selection, setSelection] = useState<GraphSelection>(null);
  const nodes = useMemo(() => fixture.nodes, [fixture.nodes]);
  const edges = useMemo(() => fixture.edges, [fixture.edges]);
  const clearSelection = useCallback(() => setSelection(null), []);

  if (state !== "ready") return <GraphState state={state} errorMessage={errorMessage} onRetry={onRetry} />;
  return <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
    <div className="overflow-hidden rounded-lg border-2 border-foreground bg-white shadow-pink">
      <div className="flex flex-col justify-between gap-3 border-b-2 border-foreground p-4 sm:flex-row sm:items-center"><div><p className="text-xs font-extrabold uppercase tracking-widest text-muted-foreground">互動風險圖</p><h2 className="mt-1 text-xl">連鎖暴露與關係狀態</h2></div><div className="flex flex-wrap gap-3 text-[10px] font-extrabold"><Legend sample="solid" label="合成直接" /><Legend sample="dashed" label="產業推論" /><Legend sample="dotted" label="未驗證" /></div></div>
      <p id="graph-help" className="sr-only">使用 Tab 鍵選取節點或連線，按 Enter 開啟詳細資訊。圖譜可以縮放及拖曳瀏覽。</p>
      <div className="h-[540px] w-full sm:h-[600px]" role="application" aria-label="合成供應鏈風險圖" aria-describedby="graph-help">
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} nodesDraggable={false} nodesConnectable={false} elementsSelectable onNodeClick={(_, item) => setSelection({ type: "node", item })} onEdgeClick={(_, item) => setSelection({ type: "edge", item })} onPaneClick={clearSelection} fitView fitViewOptions={{ padding: 0.18 }} minZoom={0.35} maxZoom={1.5} colorMode="light" proOptions={{ hideAttribution: true }}>
          <Background color="#CBD5E1" gap={24} size={1.5} variant={BackgroundVariant.Dots} />
          <Controls showInteractive={false} aria-label="圖譜縮放控制" />
          <MiniMap pannable zoomable nodeStrokeWidth={3} nodeColor={node => node.data.kind === "event" ? "#F472B6" : node.data.kind === "industry" ? "#34D399" : node.data.kind === "product" ? "#FBBF24" : node.data.kind === "region" ? "#8B5CF6" : "#FFFFFF"} maskColor="rgba(30,41,59,.08)" aria-label="圖譜縮圖" />
        </ReactFlow>
      </div>
    </div>
    <div><SelectionPanel selection={selection} onClose={clearSelection} /></div>
  </div>;
}

function Legend({ sample, label }: { sample: "solid" | "dashed" | "dotted"; label: string }) { return <span className="flex items-center gap-2"><span className={`block w-7 border-t-2 border-foreground ${sample === "dashed" ? "border-dashed !border-accent" : sample === "dotted" ? "border-dotted !border-muted-foreground" : ""}`} />{label}</span>; }
function GraphState({ state, errorMessage, onRetry }: { state: Exclude<GraphViewState, "ready">; errorMessage?: string; onRetry?: () => void }) {
  const config = state === "loading" ? { icon: LoaderCircle, title: "正在準備圖譜", text: "載入合成節點與關係中。", spin: true } : state === "empty" ? { icon: SearchX, title: "沒有可顯示的關係", text: "此情境目前沒有足夠的合成資料。", spin: false } : { icon: AlertTriangle, title: "圖譜無法顯示", text: "合成資料載入失敗，請稍後再試。", spin: false };
  const Icon = config.icon;
  return <div className="flex min-h-[420px] flex-col items-center justify-center rounded-lg border-2 border-dashed border-foreground bg-muted p-8 text-center" role={state === "error" ? "alert" : "status"}><Icon className={config.spin ? "animate-spin motion-reduce:animate-none" : ""} size={38} /><h2 className="mt-5 text-2xl">{config.title}</h2><p className="mt-2 max-w-lg text-sm text-muted-foreground">{state === "error" && errorMessage ? errorMessage : config.text}</p>{state === "error" && onRetry && <Button className="mt-6" onClick={onRetry}>重新分析</Button>}</div>;
}
