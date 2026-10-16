import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: ReactNode }) {
  return <div className="min-h-screen overflow-hidden">
    <header className="relative z-30 border-b-2 border-foreground bg-background/95 backdrop-blur">
      <div className="page-container flex min-h-20 items-center justify-between gap-5">
        <Link to="/" className="flex items-center gap-3 rounded-sm" aria-label="Domino AI 首頁">
          <span className="relative grid size-10 rotate-3 place-items-center rounded-sm border-2 border-foreground bg-tertiary font-heading text-xl shadow-hard">D</span>
          <span className="font-heading text-xl font-extrabold tracking-tight">Domino AI</span>
        </Link>
        <nav className="hidden items-center gap-1 md:flex" aria-label="主要導覽">
          {[["/", "首頁"], ["/simulate", "危機模擬"], ["/analysis/demo", "範例分析"]].map(([to, label]) =>
            <NavLink key={to} to={to} className={({ isActive }) => cn("rounded-full px-4 py-3 text-sm font-bold hover:bg-muted", isActive && "bg-foreground text-white hover:bg-foreground")}>{label}</NavLink>)}
        </nav>
        <Link to="/simulate" className="flex min-h-12 items-center gap-2 rounded-full border-2 border-foreground bg-accent px-4 text-sm font-bold text-white shadow-hard transition hover:-translate-y-0.5">開始推演 <ArrowUpRight size={17} /></Link>
      </div>
    </header>
    <main>{children}</main>
    <footer className="border-t-2 border-foreground bg-foreground py-8 text-white">
      <div className="page-container flex flex-col justify-between gap-3 text-sm sm:flex-row"><strong className="font-heading text-lg">Domino AI</strong><p className="text-slate-300">MVP 合成資料展示 · 非投資建議</p></div>
    </footer>
  </div>;
}
