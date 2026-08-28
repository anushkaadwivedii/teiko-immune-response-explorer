import { type FormEvent, useEffect, useState } from "react";
import { fetchJson } from "../api";
import { ErrorPanel, LoadingPanel } from "../components/LoadingPanel";
import type { FrequencyResponse } from "../types";

const populations = ["", "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"];
const displayName = (value: string) => value.replaceAll("_", " ");
const formatNumber = new Intl.NumberFormat("en-US");

export function Frequencies() {
  const [sampleInput, setSampleInput] = useState("");
  const [population, setPopulation] = useState("");
  const [query, setQuery] = useState({ sample: "", population: "" });
  const [data, setData] = useState<FrequencyResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ limit: "100" });
    if (query.sample) params.set("sample", query.sample);
    if (query.population) params.set("population", query.population);
    setData(null);
    setError("");
    fetchJson<FrequencyResponse>(`/api/frequencies?${params}`).then(setData).catch((reason) => {
      setError(reason instanceof Error ? reason.message : "Unknown error");
    });
  }, [query]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setQuery({ sample: sampleInput.trim(), population });
  }

  return <>
    <section className="page-heading">
      <div><p className="eyebrow">Part 2 · Data overview</p><h1>Cell frequencies</h1></div>
      <a className="button secondary" href="/api/download/frequencies">Download full CSV</a>
    </section>
    <p className="section-copy">Relative frequency is each population count divided by the total cell count for that sample. A sample contributes five rows and its percentages sum to 100%.</p>

    <form className="filter-bar" onSubmit={submit}>
      <label>Sample starts with
        <input value={sampleInput} onChange={(event) => setSampleInput(event.target.value)} placeholder="e.g. sample00000" />
      </label>
      <label>Population
        <select value={population} onChange={(event) => setPopulation(event.target.value)}>
          {populations.map((item) => <option key={item} value={item}>{item ? displayName(item) : "All populations"}</option>)}
        </select>
      </label>
      <button className="button" type="submit">Apply filters</button>
    </form>

    {error && <ErrorPanel message={error} />}
    {!data && !error && <LoadingPanel label="Loading frequency table" />}
    {data && <section className="table-panel">
      <div className="table-summary"><span>{formatNumber.format(data.total)} matching rows</span>{data.total > data.rows.length && <small>Showing the first {data.rows.length}</small>}</div>
      <div className="table-scroll"><table>
        <thead><tr><th>Sample</th><th>Total count</th><th>Population</th><th>Count</th><th>Percentage</th></tr></thead>
        <tbody>{data.rows.map((row) => <tr key={`${row.sample}-${row.population}`}>
          <td className="mono">{row.sample}</td><td>{formatNumber.format(row.total_count)}</td>
          <td><span className="population-tag">{displayName(row.population)}</span></td>
          <td>{formatNumber.format(row.count)}</td><td><strong>{row.percentage.toFixed(2)}%</strong></td>
        </tr>)}</tbody>
      </table></div>
    </section>}
  </>;
}
