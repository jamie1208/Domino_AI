import { FlaskConical } from "lucide-react";
import { cn } from "@/lib/utils";

export function SyntheticBadge({ className, compact = false }: { className?: string; compact?: boolean }) {
  return <div className={cn("inline-flex items-center gap-2 rounded-full border-2 border-foreground bg-tertiary px-3 py-1.5 text-xs font-extrabold", className)} role="status"><FlaskConical size={15} aria-hidden />{compact ? "合成資料" : "合成資料／非實際企業分析"}</div>;
}
