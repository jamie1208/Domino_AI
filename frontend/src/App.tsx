import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/app-shell";
import { AnalysisPage } from "@/pages/analysis-page";
import { CompanyPage } from "@/pages/company-page";
import { HomePage } from "@/pages/home-page";
import { SimulationPage } from "@/pages/simulation-page";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/simulate" element={<SimulationPage />} />
        <Route path="/analysis/demo" element={<AnalysisPage />} />
        <Route path="/company/demo" element={<CompanyPage />} />
      </Routes>
    </AppShell>
  );
}
