import { Building2, Link2, MousePointerClick, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DominoEdgeData, GraphSelection } from "@/types/graph";

const nodeKindLabels = { event: "事件節點", region: "地區節點", product: "產品節點", industry: "產業節點", company: "企業節點" } as const;
const edgeKindLabels = { verified_direct: "合成直接關係", industry_inferred: "產業推論", unverified_candidate: "未驗證候選" } as const;

export function SelectionPanel({ selection, onClose }: { selection: GraphSelection; onClose: () => void }) {
  if (!selection) return <EmptySelection />;

  if (selection.type === "node") {
    const data = selection.item.data;
    return <PanelShell icon={<Building2 size={20} />} onClose={onClose}>
      <p className="mt-5 text-xs font-extrabold uppercase tracking-widest text-muted-foreground">{nodeKindLabels[data.kind]}</p>
      <h3 className="mt-1 text-2xl">{data.label}</h3>
      <p className="mt-4 text-sm leading-6 text-muted-foreground">{data.description}</p>
      <Definition label="資料狀態" value={data.status} />
      {data.riskLabel && <><Definition label="暴露標籤" value={data.riskLabel} /><Definition label="合成測試索引" value={String(data.fixtureRiskIndex)} /></>}
    </PanelShell>;
  }

  if (!selection.item.data) return <EmptySelection />;
  const data: DominoEdgeData = selection.item.data;
  return <PanelShell icon={<Link2 size={20} />} onClose={onClose} edge>
    <p className="mt-5 text-xs font-extrabold uppercase tracking-widest text-muted-foreground">{edgeKindLabels[data.kind]}</p>
    <h3 className="mt-1 text-2xl">{data.relationLabel}</h3>
    <p className="mt-4 text-sm leading-6 text-muted-foreground">{data.description}</p>
    <Definition label="證據狀態" value={data.evidenceStatus} />
    <Definition label="納入傳播" value={data.includedInPropagation ? "是（合成範例）" : "否"} />
    <Definition label="引用" value={data.evidenceIds.length ? data.evidenceIds.join("、") : "無真實引用（fixture）"} />
    {data.evidenceSummaries?.length ? <Definition label="合成證據標題" value={data.evidenceSummaries.join("；")} /> : null}
  </PanelShell>;
}

function EmptySelection() { return <aside className="flex min-h-64 flex-col items-center justify-center rounded-lg border-2 border-dashed border-foreground bg-muted p-7 text-center" aria-live="polite"><MousePointerClick size={30} /><h3 className="mt-4 text-lg">選取圖譜元素</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">點選節點或關係連線，查看合成資訊與驗證狀態。</p></aside>; }
function PanelShell({ children, icon, onClose, edge = false }: { children: React.ReactNode; icon: React.ReactNode; onClose: () => void; edge?: boolean }) { return <aside className="rounded-lg border-2 border-foreground bg-white p-6 shadow-hard" aria-live="polite" aria-label="圖譜資訊面板"><div className="flex items-start justify-between gap-4"><span className={`grid size-11 place-items-center rounded-full border-2 border-foreground ${edge ? "bg-tertiary" : "bg-quaternary"}`}>{icon}</span><Button variant="ghost" className="size-12 px-0" onClick={onClose} aria-label="關閉資訊面板"><X size={20} /></Button></div>{children}<div className="mt-5 rounded-md border-2 border-dashed border-foreground bg-tertiary/40 p-3 text-xs font-bold">合成資料／非實際企業分析</div></aside>; }
function Definition({ label, value }: { label: string; value: string }) { return <div className="mt-4 border-t-2 border-border pt-3 text-sm"><span className="block text-xs text-muted-foreground">{label}</span><strong className="mt-1 block">{value}</strong></div>; }
