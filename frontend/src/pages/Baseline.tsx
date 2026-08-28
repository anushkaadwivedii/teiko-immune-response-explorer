import { useEffect, useState } from "react";
import { fetchJson } from "../api";
import { ErrorPanel, LoadingPanel } from "../components/LoadingPanel";
import type { BaselineSummary } from "../types";

const formatNumber = new Intl.NumberFormat("en-US");

function Breakdown({ title, values, total }: { title: string; values: Record<string, number>; total: number }) {
  return <article className="panel breakdown-card"><p className="eyebrow">{title}</p>
    {Object.entries(values).map(([label, count]) => <div className="progress-row" key={label}>
      <div><span>{label}</span><strong>{formatNumber.format(count)}</strong></div>
      <div className="progress-track"><span style={{ width: `${(count / total) * 100}%` }} /></div>
    </div>)}
  </article>;
}

export function Baseline() {
  const [data, setData] = useState<BaselineSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchJson<BaselineSummary>("/api/baseline-summary").then(setData).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Unknown error");
    });
  }, []);

  if (error) return <ErrorPanel message={error} />;
  if (!data) return <LoadingPanel label="Loading baseline cohort" />;

  return <>
    <section className="page-heading">
      <div><p className="eyebrow">Part 4 · Subset analysis</p><h1>Baseline cohort</h1></div>
      <span className="cohort-chip">Day 0</span>
    </section>
    <p className="section-copy">Melanoma PBMC samples collected at treatment start from subjects receiving miraclib.</p>

    <section className="baseline-hero">
      <article className="baseline-total"><span>Qualifying samples</span><strong>{formatNumber.format(data.baseline_sample_count)}</strong><small>{formatNumber.format(data.baseline_subject_count)} distinct subjects</small></article>
      <article className="answer-card"><p className="eyebrow">Requested calculation</p><span>Average B-cell count</span><strong>{formatNumber.format(data.average_b_cells_melanoma_male_responders_time_0)}</strong><small>Melanoma male responders · all sample and treatment types · day 0</small></article>
    </section>

    <section className="breakdown-grid">
      <Breakdown title="Samples by project" values={data.samples_by_project} total={data.baseline_sample_count} />
      <Breakdown title="Subjects by response" values={data.subjects_by_response} total={data.baseline_subject_count} />
      <Breakdown title="Subjects by sex" values={data.subjects_by_sex} total={data.baseline_subject_count} />
    </section>
  </>;
}
