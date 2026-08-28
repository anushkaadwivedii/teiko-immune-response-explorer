from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.analysis import calculate_statistical_results, response_analysis_values


ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "cell-count.db"
OUTPUT_DIR = ROOT / "outputs"
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Teiko Immune Response API",
    description="Clinical immune cell frequency and treatment response analysis",
    version="1.0.0",
)


def database_connection() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="The analysis database is not available. Run make pipeline first.",
        )
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def rows_as_dicts(rows: list[sqlite3.Row]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok" if DATABASE_PATH.exists() else "database_missing"}


@app.get("/api/overview")
def overview() -> dict[str, object]:
    with database_connection() as connection:
        counts = {
            "projects": connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
            "subjects": connection.execute("SELECT COUNT(*) FROM subjects").fetchone()[0],
            "samples": connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0],
            "cell_measurements": connection.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0],
        }
        sample_types = rows_as_dicts(connection.execute(
            "SELECT sample_type AS label, COUNT(*) AS count FROM samples GROUP BY sample_type ORDER BY count DESC"
        ).fetchall())
        conditions = rows_as_dicts(connection.execute(
            "SELECT condition AS label, COUNT(*) AS count FROM subjects GROUP BY condition ORDER BY count DESC"
        ).fetchall())
        projects = rows_as_dicts(connection.execute(
            """
            SELECT p.project_code AS label, COUNT(s.sample_id) AS count
            FROM projects AS p
            LEFT JOIN subjects AS sub ON sub.project_id = p.project_id
            LEFT JOIN samples AS s ON s.subject_id = sub.subject_id
            GROUP BY p.project_id
            ORDER BY p.project_code
            """
        ).fetchall())

    pipeline_summary_path = OUTPUT_DIR / "pipeline_summary.json"
    response_signal = None
    baseline_response_signal = None
    if pipeline_summary_path.exists():
        pipeline_summary = json.loads(
            pipeline_summary_path.read_text(encoding="utf-8")
        )
        response_signal = pipeline_summary.get("response_signal")
        baseline_response_signal = pipeline_summary.get("baseline_response_signal")

    return {
        "counts": counts,
        "sample_types": sample_types,
        "conditions": conditions,
        "projects": projects,
        "response_signal": response_signal,
        "baseline_response_signal": baseline_response_signal,
    }


@app.get("/api/frequencies")
def frequencies(
    sample: str | None = Query(default=None, max_length=50),
    population: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    conditions: list[str] = []
    parameters: list[object] = []
    if sample:
        conditions.append("sample LIKE ?")
        parameters.append(f"{sample}%")
    if population:
        conditions.append("population = ?")
        parameters.append(population)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    with database_connection() as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM sample_population_frequencies {where_clause}", parameters
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT sample, total_count, population, count, percentage
            FROM sample_population_frequencies
            {where_clause}
            ORDER BY sample, population
            LIMIT ? OFFSET ?
            """,
            [*parameters, limit, offset],
        ).fetchall()
    return {"total": total, "rows": rows_as_dicts(rows)}


@app.get("/api/response-analysis")
def response_analysis() -> dict[str, object]:
    with database_connection() as connection:
        subject_values = response_analysis_values(connection)
        baseline_values = response_analysis_values(
            connection, time_from_treatment_start=0
        )
    statistics = calculate_statistical_results(subject_values)
    baseline_statistics = calculate_statistical_results(baseline_values)
    return {
        "subject_count": int(subject_values["subject_key"].nunique()),
        "values": subject_values.to_dict(orient="records"),
        "statistics": statistics.to_dict(orient="records"),
        "baseline_values": baseline_values.to_dict(orient="records"),
        "baseline_statistics": baseline_statistics.to_dict(orient="records"),
    }


@app.get("/api/baseline-summary")
def baseline_summary() -> dict[str, object]:
    summary_path = OUTPUT_DIR / "baseline_summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=503, detail="Baseline outputs are missing. Run make pipeline first.")
    return json.loads(summary_path.read_text(encoding="utf-8"))


@app.get("/api/download/frequencies")
def download_frequencies() -> FileResponse:
    frequency_path = OUTPUT_DIR / "sample_frequencies.csv"
    if not frequency_path.exists():
        raise HTTPException(status_code=503, detail="Frequency output is missing. Run make pipeline first.")
    return FileResponse(frequency_path, media_type="text/csv", filename="sample_frequencies.csv")


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
