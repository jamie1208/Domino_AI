import { Factory, PackageOpen, ShipWheel } from "lucide-react";

export const demoScenarios = [
  { icon: PackageOpen, label: "材料中斷", title: "測試材料供應中斷 30 天", meta: "虛構地區 · 合成案例", color: "bg-secondary" },
  { icon: ShipWheel, label: "物流延誤", title: "測試港口暫停作業 14 天", meta: "虛構港口 · 合成案例", color: "bg-tertiary" },
  { icon: Factory, label: "產能下降", title: "測試零件產能下降 40%", meta: "虛構產業 · 合成案例", color: "bg-quaternary" },
] as const;

export const demoCompanies = [
  { name: "範例元件 A", sector: "測試零組件", risk: 78, level: "高暴露", color: "bg-secondary" },
  { name: "範例製造 B", sector: "測試製造業", risk: 61, level: "中度暴露", color: "bg-tertiary" },
  { name: "範例通路 C", sector: "測試通路業", risk: 34, level: "低度暴露", color: "bg-quaternary" },
] as const;
