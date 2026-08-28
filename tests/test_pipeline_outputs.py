import csv
import json
import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
DATABASE_PATH = ROOT / "cell-count.db"
OUTPUT_DIR = ROOT / "outputs"
POPULATIONS = {"b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"}


def test_required_pipeline_artifacts_exist() -> None:
    required_files = [
        ROOT / "cell-count.db",
        OUTPUT_DIR / "sample_frequencies.csv",
        OUTPUT_DIR / "response_analysis_values.csv",
        OUTPUT_DIR / "statistical_results.csv",
        OUTPUT_DIR / "response_boxplots.png",
        OUTPUT_DIR / "baseline_samples.csv",
        OUTPUT_DIR / "baseline_samples_by_project.csv",
        OUTPUT_DIR / "baseline_subjects_by_response.csv",
        OUTPUT_DIR / "baseline_subjects_by_sex.csv",
        OUTPUT_DIR / "baseline_summary.json",
    ]

    assert all(path.is_file() and path.stat().st_size > 0 for path in required_files)


def test_generated_frequency_table_matches_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        sample_count = connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        database_rows = connection.execute(
            "SELECT COUNT(*) FROM sample_population_frequencies"
        ).fetchone()[0]

    with (OUTPUT_DIR / "sample_frequencies.csv").open(
        newline="", encoding="utf-8"
    ) as source:
        reader = csv.DictReader(source)
        assert reader.fieldnames == [
            "sample",
            "total_count",
            "population",
            "count",
            "percentage",
        ]
        rows = list(reader)

    assert len(rows) == database_rows == sample_count * len(POPULATIONS)
    assert {row["population"] for row in rows} == POPULATIONS

    percentage_totals: dict[str, float] = {}
    for row in rows:
        percentage_totals[row["sample"]] = percentage_totals.get(
            row["sample"], 0.0
        ) + float(row["percentage"])
    assert all(total == pytest.approx(100.0) for total in percentage_totals.values())


def test_statistical_and_baseline_outputs_are_complete() -> None:
    with (OUTPUT_DIR / "statistical_results.csv").open(
        newline="", encoding="utf-8"
    ) as source:
        statistics = list(csv.DictReader(source))

    assert {row["population"] for row in statistics} == POPULATIONS
    assert all(0 <= float(row["p_value"]) <= 1 for row in statistics)
    assert all(0 <= float(row["adjusted_p_value"]) <= 1 for row in statistics)

    summary = json.loads((OUTPUT_DIR / "baseline_summary.json").read_text())
    assert summary["baseline_sample_count"] == sum(
        summary["samples_by_project"].values()
    )
    assert summary["baseline_subject_count"] == sum(
        summary["subjects_by_response"].values()
    )
    assert summary["baseline_subject_count"] == sum(
        summary["subjects_by_sex"].values()
    )
    assert summary["average_b_cells_melanoma_male_responders_time_0"] == pytest.approx(
        10206.15
    )
