import { ArrowRight, Check, Network, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SyntheticBadge } from "@/components/synthetic-badge";
import { demoScenarios } from "@/data/mock-data";

export function HomePage() {
  return <>
    <section className="relative border-b-2 border-foreground py-20 sm:py-28">
      <div className="pointer-events-none absolute left-[5%] top-16 size-20 rotate-12 rounded-lg border-2 border-foreground bg-secondary/40" />
      <div className="pointer-events-none absolute bottom-12 right-[6%] size-16 rounded-full border-2 border-foreground bg-quaternary/50" />
      <div className="page-container relative grid items-center gap-14 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <span className="eyebrow mb-7 bg-white"><Sparkles size={15} /> 供應鏈風險推演</span>
          <h1 className="max-w-3xl text-5xl font-extrabold leading-[.98] tracking-[-.04em] sm:text-7xl">一個事件，<br /><span className="relative text-accent">會推倒哪些骨牌？<svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 340 12" aria-hidden><path d="M3 8c78-8 204 6 334-4" fill="none" stroke="#F472B6" strokeWidth="6" strokeLinecap="round" /></svg></span></h1>
          <p className="mt-9 max-w-xl text-lg leading-8 text-muted-foreground">把危機情境轉成可追溯的風險路徑，清楚看見產業與企業之間的連鎖暴露。</p>
          <div className="mt-9 flex flex-col gap-4 sm:flex-row"><Button asChild><Link to="/simulate">開始危機推演 <ArrowRight size={18} /></Link></Button><Button asChild variant="secondary"><Link to="/analysis/demo">查看合成範例</Link></Button></div>
          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold">{["路徑可解釋", "證據狀態清楚", "相對暴露索引"].map(x => <span key={x} className="flex items-center gap-2"><span className="grid size-5 place-items-center rounded-full bg-quaternary"><Check size={13} strokeWidth={3} /></span>{x}</span>)}</div>
        </div>
        <div className="relative lg:col-span-5">
          <Card className="relative min-h-[390px] overflow-hidden p-7 shadow-pink grid-paper">
            <SyntheticBadge />
            <div className="mt-9 flex justify-center"><div className="grid size-24 place-items-center rounded-full border-2 border-foreground bg-secondary text-center text-sm font-bold shadow-hard">供應<br />中斷</div></div>
            <div className="mx-auto h-10 w-0.5 bg-foreground" />
            <div className="grid grid-cols-2 gap-10"><div className="rounded-md border-2 border-foreground bg-tertiary p-4 text-center text-sm font-bold shadow-hard">材料產業</div><div className="rounded-md border-2 border-dashed border-foreground bg-white p-4 text-center text-sm font-bold">製造產業</div></div>
            <Network className="absolute bottom-4 right-5 text-accent" size={30} />
          </Card>
        </div>
      </div>
    </section>
    <section className="page-container py-20"><div className="mb-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><span className="eyebrow mb-4">從範例開始</span><h2 className="text-3xl font-extrabold sm:text-4xl">如果今天發生⋯⋯</h2></div><p className="max-w-sm text-sm leading-6 text-muted-foreground">以下皆為虛構情境，用來展示介面流程，不代表真實事件或企業關係。</p></div>
      <div className="grid gap-6 md:grid-cols-3">{demoScenarios.map(({ icon: Icon, ...item }) => <Card key={item.title} className="group p-6 shadow-yellow transition hover:-translate-y-1"><div className={`grid size-12 place-items-center rounded-full border-2 border-foreground ${item.color}`}><Icon size={22} /></div><p className="mt-7 text-xs font-extrabold uppercase tracking-widest text-muted-foreground">{item.label}</p><h3 className="mt-2 text-xl leading-7">{item.title}</h3><p className="mt-5 border-t-2 border-dashed border-border pt-4 text-sm text-muted-foreground">{item.meta}</p></Card>)}</div>
    </section>
  </>;
}
