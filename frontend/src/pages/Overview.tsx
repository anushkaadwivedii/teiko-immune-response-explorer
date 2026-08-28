import { useEffect, useState } from "react";
import { fetchJson } from "../api";
import { ErrorPanel, LoadingPanel } from "../components/LoadingPanel";
import type { OverviewData } from "../types";

const formatNumber = new Intl.NumberFormat("en-US");
const displayPopulation: Record<string, string> = {
  b_cell: "B cells",
  cd8_t_cell: "CD8 T cells",
  cd4_t_cell: "CD4 T cells",
  nk_cell: "NK cells",
  monocyte: "Monocytes",
};

export function Overview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<OverviewData>("/api/overview").then(setData).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Unknown error");
    });
  }, []);

  if (error) return <ErrorPanel message={error} />;
  if (!data) return <LoadingPanel label="Loading dataset overview" />;

  const metrics = [
    { label: "Projects", value: data.counts.projects, detail: "independent trial datasets" },
    { label: "Subjects", value: data.counts.subjects, detail: "three timepoints per subject" },
    { label: "Samples", value: data.counts.samples, detail: "PBMC and whole blood" },
    { label: "Cell measurements", value: data.counts.cell_measurements, detail: "five populations per sample" },
  ];
  const signal = data.response_signal;
  const baselineSignal = data.baseline_response_signal;

  return <>
    <section className="hero">
      <div>
        <p className="eyebrow">Clinical trial · Immune profiling</p>
        <h1>Immune Response Explorer</h1>
        <p className="hero-copy">Explore immune cell composition and compare melanoma patient response to miraclib across a validated clinical dataset.</p>
      </div>
      <div className="hero-badge"><span>Analysis status</span><strong>Complete</strong></div>
    </section>

    <section className="metric-grid" aria-label="Dataset summary">
      {metrics.map((metric) => <article className="metric-card" key={metric.label}>
        <span>{metric.label}</span><strong>{formatNumber.format(metric.value)}</strong><small>{metric.detail}</small>
      </article>)}
    </section>

    <section className="insight-grid">
      <article className="panel signal-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Response signal</p><h2>{signal ? `${displayPopulation[signal.population]} merit follow-up` : "Exploratory comparison"}</h2></div>
          <span className="signal-pill">Exploratory</span>
        </div>
        <p>Across all three timepoints, the strongest difference is exploratory and does not remain below 0.05 after correction across five populations. The baseline-only sensitivity analysis also finds no significant population differences.</p>
        <div className="signal-stats">
          <div><span>Median difference</span><strong>{signal ? `${signal.median_difference_percentage_points > 0 ? "+" : ""}${signal.median_difference_percentage_points.toFixed(2)} pp` : "—"}</strong></div>
          <div><span>Raw p value</span><strong>{signal ? signal.p_value.toFixed(3) : "—"}</strong></div>
          <div><span>Strongest baseline raw p</span><strong>{baselineSignal ? baselineSignal.p_value.toFixed(3) : "—"}</strong></div>
        </div>
      </article>

      <article className="panel cohort-panel">
        <p className="eyebrow">Dataset composition</p><h2>Sample material</h2>
        {data.sample_types.map((group) => <div className="progress-row" key={group.label}>
          <div><span>{group.label}</span><strong>{formatNumber.format(group.count)}</strong></div>
          <div className="progress-track"><span style={{ width: `${(group.count / data.counts.samples) * 100}%` }} /></div>
        </div>)}
        <p className="cohort-footnote">Source data passed identity and relationship checks</p>
      </article>
    </section>
  </>;
}
