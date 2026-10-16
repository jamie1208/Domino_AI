import { Building2, Factory, Globe2, Package, TriangleAlert, type LucideIcon } from "lucide-react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { DominoNode, DominoNodeKind } from "@/types/graph";

const nodeDesign: Record<DominoNodeKind, { icon: LucideIcon; color: string; shape: string }> = {
  event: { icon: TriangleAlert, color: "bg-secondary", shape: "rounded-full" },
  region: { icon: Globe2, color: "bg-accent text-white", shape: "rounded-lg" },
  product: { icon: Package, color: "bg-tertiary", shape: "rounded-sm" },
  industry: { icon: Factory, color: "bg-quaternary", shape: "rounded-lg" },
  company: { icon: Building2, color: "bg-white", shape: "rounded-md" },
};

export function DominoNodeView({ data, selected }: NodeProps<DominoNode>) {
  const design = nodeDesign[data.kind];
  const Icon = design.icon;
  return <div className={cn("domino-node min-w-[180px] border-2 border-foreground p-3 shadow-hard", design.color, design.shape, selected && "ring-4 ring-accent ring-offset-2", data.onImportantPath && "important-node")} aria-label={`${data.caption}：${data.label}${data.riskLabel ? `，${data.riskLabel}` : ""}`}>
    <Handle type="target" position={Position.Left} className="!size-3 !border-2 !border-foreground !bg-background" />
    <div className="flex items-center gap-3"><span className="grid size-9 shrink-0 place-items-center rounded-full border-2 border-foreground bg-background text-foreground"><Icon size={18} aria-hidden /></span><span className="min-w-0"><span className="block text-[10px] font-extrabold uppercase tracking-widest opacity-70">{data.caption}</span><strong className="block truncate font-heading text-sm">{data.label}</strong></span></div>
    {data.riskLabel && <span className="mt-2 inline-flex rounded-full border border-foreground px-2 py-0.5 text-[10px] font-extrabold">{data.riskLabel} · 合成索引 {data.fixtureRiskIndex}</span>}
    {data.onImportantPath && <span className="mt-2 block text-[9px] font-extrabold uppercase tracking-wider">◆ 重要路徑</span>}
    <Handle type="source" position={Position.Right} className="!size-3 !border-2 !border-foreground !bg-background" />
  </div>;
}
