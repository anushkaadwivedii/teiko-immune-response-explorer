import { lazy, Suspense, useState } from "react";
import { LoadingPanel } from "./components/LoadingPanel";
import { Baseline } from "./pages/Baseline";
import { Frequencies } from "./pages/Frequencies";
import { Overview } from "./pages/Overview";
import type { Page } from "./types";

const ResponseAnalysis = lazy(() =>
  import("./pages/ResponseAnalysis").then((module) => ({ default: module.ResponseAnalysis })),
);

const navigation: { page: Page; label: string }[] = [
  { page: "overview", label: "Overview" },
  { page: "frequencies", label: "Cell frequencies" },
  { page: "response", label: "Response analysis" },
  { page: "baseline", label: "Baseline cohort" },
];

function App() {
  const [page, setPage] = useState<Page>("overview");

  return <div className="app-shell">
    <aside className="sidebar">
      <button className="brand" type="button" onClick={() => setPage("overview")} aria-label="Teiko analysis home">
        <span className="brand-mark">T</span><span><strong>Teiko</strong><small>Clinical analytics</small></span>
      </button>
      <nav aria-label="Dashboard sections">
        {navigation.map((item) => <button
          className={`nav-item ${page === item.page ? "active" : ""}`}
          aria-current={page === item.page ? "page" : undefined}
          key={item.page}
          type="button"
          onClick={() => setPage(item.page)}
        >{item.label}</button>)}
      </nav>
      <div className="sidebar-note"><span className="status-dot" /><div><strong>Dataset ready</strong><small>10,500 samples validated</small></div></div>
    </aside>

    <main>
      {page === "overview" && <Overview />}
      {page === "frequencies" && <Frequencies />}
      {page === "response" && <Suspense fallback={<LoadingPanel label="Loading interactive chart" />}><ResponseAnalysis /></Suspense>}
      {page === "baseline" && <Baseline />}
    </main>
  </div>;
}

export default App;
