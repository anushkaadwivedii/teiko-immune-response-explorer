import { useEffect, useState } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-cartesian-dist-min";
import type { Layout } from "plotly.js";
import { fetchJson } from "../api";
import { ErrorPanel, LoadingPanel } from "../components/LoadingPanel";
import type { ResponseAnalysisData } from "../types";

const populationOrder = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"];
const Plot = createPlotlyComponent(Plotly);
const names: Record<string, string> = {
  b_cell: "B cell", cd8_t_cell: "CD8 T cell", cd4_t_cell: "CD4 T cell", nk_cell: "NK cell", monocyte: "Monocyte",
};

function formatPValue(value: number) {
  return value < 0.001 ? value.toExponential(2) : value.toFixed(3);
}

export function ResponseAnalysis() {
  const [data, setData] = useState<ResponseAnalysisData | null>(null);
  const [error, setError] = useState("");
  const [scope, setScope] = useState<"all" | "baseline">("all");

  useEffect(() => {
    fetchJson<ResponseAnalysisData>("/api/response-analysis").then(setData).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Unknown error");
    });
  }, []);

  if (error) return <ErrorPanel message={error} />;
  if (!data) return <LoadingPanel label="Running response comparison" />;

  const values = scope === "all" ? data.values : data.baseline_values;
  const statistics = scope === "all" ? data.statistics : data.baseline_statistics;

  const traces = (["yes", "no"] as const).map((response) => ({
    type: "box" as const,
    name: response === "yes" ? "Responder" : "Nonresponder",
    x: values.filter((row) => row.response === response).map((row) => names[row.population]),
    y: values.filter((row) => row.response === response).map((row) => row.mean_percentage),
    marker: { color: response === "yes" ? "#16879a" : "#d79b39" },
    boxpoints: "outliers" as const,
    jitter: 0.25,
    pointpos: 0,
    hovertemplate: "%{x}<br>%{y:.2f}%<extra>%{fullData.name}</extra>",
  }));
  const layout: Partial<Layout> & { boxmode: "group" } = {
    autosize: true,
    boxmode: "group",
    margin: { l: 62, r: 20, t: 32, b: 62 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: { family: "Inter, system-ui, sans-serif", color: "#4f676a", size: 12 },
    legend: { orientation: "h", x: 0, y: 1.14 },
    xaxis: {
      title: { text: "Immune cell population", standoff: 18 },
      categoryorder: "array",
      categoryarray: populationOrder.map((item) => names[item]),
      gridcolor: "#eef2f1",
    },
    yaxis: {
      title: { text: "Subject mean relative frequency (%)", standoff: 12 },
      gridcolor: "#e7edeb",
      zeroline: false,
    },
  };

  return <>
    <section className="page-heading">
      <div><p className="eyebrow">Part 3 · Statistical analysis</p><h1>Response analysis</h1></div>
      <span className="cohort-chip">{data.subject_count} subjects</span>
    </section>
    <p className="section-copy">Melanoma subjects receiving miraclib with PBMC samples only. Compare the full repeated-measures association with the baseline-only view that is appropriate for prediction.</p>

    <div className="segmented-control" aria-label="Analysis scope">
      <button type="button" className={scope === "all" ? "selected" : ""} aria-pressed={scope === "all"} onClick={() => setScope("all")}>All timepoints · subject mean</button>
      <button type="button" className={scope === "baseline" ? "selected" : ""} aria-pressed={scope === "baseline"} onClick={() => setScope("baseline")}>Baseline only · day 0</button>
    </div>

    <section className="chart-panel">
      <Plot
        key={scope}
        data={traces}
        layout={layout}
        config={{ responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] }}
        useResizeHandler
        style={{ width: "100%", height: "500px" }}
      />
    </section>

    <section className="result-note"><span className="signal-pill">Interpretation</span><p>{scope === "all" ? "CD4 T cells have the smallest raw p value across the three timepoints, but no population remains below 0.05 after false discovery rate correction. Because this view includes post-treatment samples, it describes association rather than baseline prediction." : "No baseline population has a raw or adjusted p value below 0.05. This dataset does not provide evidence that baseline relative frequency alone predicts miraclib response."}</p></section>

    <section className="table-panel statistics-table">
      <div className="table-summary"><span>Two-sided Mann–Whitney U results</span><small>Benjamini–Hochberg correction across five populations</small></div>
      <div className="table-scroll"><table>
        <thead><tr><th>Population</th><th>Responder median</th><th>Nonresponder median</th><th>Difference</th><th>Raw p</th><th>Adjusted p</th><th>Effect size</th></tr></thead>
        <tbody>{statistics.map((row) => <tr key={row.population} className={row.nominally_significant_at_0_05 ? "highlight-row" : ""}>
          <td><strong>{names[row.population]}</strong></td><td>{row.responder_median_percentage.toFixed(2)}%</td>
          <td>{row.nonresponder_median_percentage.toFixed(2)}%</td>
          <td className={row.median_difference_percentage_points > 0 ? "positive" : "negative"}>{row.median_difference_percentage_points > 0 ? "+" : ""}{row.median_difference_percentage_points.toFixed(2)} pp</td>
          <td>{formatPValue(row.p_value)}</td><td><strong>{formatPValue(row.adjusted_p_value)}</strong></td><td>{row.rank_biserial_effect_size.toFixed(3)}</td>
        </tr>)}</tbody>
      </table></div>
    </section>
  </>;
}
