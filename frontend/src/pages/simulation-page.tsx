import { useState, type FormEvent } from "react";
import { ArrowRight, Info, SlidersHorizontal } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { PageHeading } from "@/components/page-heading";
import { SyntheticBadge } from "@/components/synthetic-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Select, Textarea } from "@/components/ui/form-controls";
import { DEFAULT_DEMO_SCENARIO } from "@/services/analysis-api";
import type { ScenarioRequest } from "@/types/api";

export function SimulationPage() {
  const navigate = useNavigate();
  const [scenario, setScenario] = useState<ScenarioRequest>(DEFAULT_DEMO_SCENARIO);
  const [error, setError] = useState("");
  const update = <K extends keyof ScenarioRequest>(key: K, value: ScenarioRequest[K]) => setScenario(current => ({ ...current, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (scenario.description.trim().length < 3) { setError("危機描述至少需要 3 個字元。"); return; }
    setError("");
    navigate("/analysis/demo", { state: { scenario } });
  };

  return <section className="page-container py-12 sm:py-16"><PageHeading eyebrow="Scenario Builder" title="描述你想推演的危機" description="先用自然語言寫下情境，再調整可確認的條件。尚未提供的資訊會以 null 送出，不會被自動當成事實。" aside={<SyntheticBadge />} />
    <div className="mt-10 grid gap-8 lg:grid-cols-12"><Card className="p-6 shadow-pink sm:p-8 lg:col-span-8"><div className="flex items-center gap-3"><div className="grid size-10 place-items-center rounded-full border-2 border-foreground bg-accent text-white"><SlidersHorizontal size={19} /></div><div><p className="text-xs font-bold text-muted-foreground">步驟 1 / 2</p><h2 className="text-2xl">建立情境</h2></div></div>
      <form className="mt-8 space-y-7" onSubmit={submit}><label className="block"><span className="mb-2 block text-sm font-bold">危機描述</span><Textarea value={scenario.description} onChange={event => update("description", event.target.value)} aria-describedby="description-help" required minLength={3} /><span id="description-help" className="mt-2 block text-xs text-muted-foreground">請勿輸入機密資料；送出後會傳至本機示範 API。</span></label>
        <div className="grid gap-5 sm:grid-cols-2"><Field label="事件類型"><Select value={scenario.event_type} onChange={event => update("event_type", event.target.value as ScenarioRequest["event_type"])}><option value="supply_chain">供應鏈中斷</option><option value="natural_disaster">自然災害</option><option value="economic_policy">經濟政策</option><option value="unknown">未知</option></Select></Field><Field label="地區"><Input value={scenario.region ?? ""} onChange={event => update("region", event.target.value || null)} /></Field><Field label="產品"><Input value={scenario.product ?? ""} onChange={event => update("product", event.target.value || null)} /></Field><Field label="持續時間（天）"><Input type="number" min="0" max="3650" value={scenario.duration_days ?? ""} onChange={event => update("duration_days", event.target.value ? Number(event.target.value) : null)} /></Field><Field label="嚴重程度"><Select value={scenario.severity ?? ""} onChange={event => update("severity", event.target.value ? Number(event.target.value) : null)}><option value="">未知／尚未提供</option><option value="0.35">低（示範參數 0.35）</option><option value="0.65">中（示範參數 0.65）</option><option value="0.8">高（示範參數 0.8）</option></Select></Field><Field label="起始暴露節點"><Input value={scenario.seed_nodes.join(", ")} onChange={event => update("seed_nodes", event.target.value.split(",").map(item => item.trim()).filter(Boolean))} aria-describedby="seed-help" /><span id="seed-help" className="mt-2 block text-xs text-muted-foreground">多個節點請用半形逗號分隔。</span></Field></div>
        <div className="rounded-md border-2 border-dashed border-foreground bg-muted p-4 text-sm leading-6"><strong>嚴重程度目前為：{scenario.severity === null ? "未知" : `已提供（${scenario.severity}）`}</strong><p className="text-muted-foreground">數值只會送往 Python risk engine；React 不會計算或改寫風險索引。</p></div>
        {error && <p role="alert" className="rounded-md border-2 border-foreground bg-secondary/30 p-4 text-sm font-bold">{error}</p>}
        <Button type="submit" className="w-full sm:w-auto">送出並執行合成分析 <ArrowRight size={18} /></Button></form></Card>
      <aside className="space-y-5 lg:col-span-4"><Card className="bg-tertiary p-6 shadow-hard"><Info size={24} /><h2 className="mt-4 text-xl">這一版會做什麼？</h2><ul className="mt-4 space-y-3 text-sm font-medium">{["送出一致的 API Schema", "由 Python 計算合成風險", "以互動圖顯示 API 結果"].map(item => <li key={item} className="flex gap-2"><span aria-hidden>◆</span>{item}</li>)}</ul></Card><p className="rounded-md border-2 border-foreground bg-white p-5 text-xs leading-5 text-muted-foreground"><strong className="text-foreground">注意：</strong> 此 MVP 不預測事件發生機率、實際損失或投資表現。</p></aside></div>
  </section>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-2 block text-sm font-bold">{label}</span>{children}</label>; }
