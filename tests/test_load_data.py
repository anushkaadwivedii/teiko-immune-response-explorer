import csv
import sqlite3
from pathlib import Path

import pytest

from backend.database import DataValidationError, build_database


POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "project",
        "subject",
        "condition",
        "age",
        "sex",
        "treatment",
        "response",
        "sample",
        "sample_type",
        "time_from_treatment_start",
        *POPULATIONS,
    ]
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sample_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "project": "prj1",
        "subject": "sbj1",
        "condition": "melanoma",
        "age": 58,
        "sex": "F",
        "treatment": "miraclib",
        "response": "yes",
        "sample": "sample1",
        "sample_type": "PBMC",
        "time_from_treatment_start": 0,
        "b_cell": 10,
        "cd8_t_cell": 20,
        "cd4_t_cell": 30,
        "nk_cell": 15,
        "monocyte": 25,
    }
    row.update(overrides)
    return row


def build_test_database(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    csv_path = tmp_path / "cell-count.csv"
    database_path = tmp_path / "cell-count.db"
    schema_path = Path(__file__).parents[1] / "backend" / "schema.sql"
    write_csv(csv_path, rows)
    build_database(csv_path, database_path, schema_path)
    return database_path


def test_database_contains_normalized_rows_and_frequency_view(tmp_path: Path) -> None:
    database_path = build_test_database(tmp_path, [sample_row()])

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM cell_counts").fetchone()[0] == 5
        frequency_rows = connection.execute(
            """
            SELECT population, count, total_count, percentage
            FROM sample_population_frequencies
            ORDER BY population
            """
        ).fetchall()

    assert len(frequency_rows) == 5
    assert all(row[2] == 100 for row in frequency_rows)
    assert sum(row[3] for row in frequency_rows) == pytest.approx(100.0)


def test_blank_response_is_stored_as_null(tmp_path: Path) -> None:
    database_path = build_test_database(tmp_path, [sample_row(response="")])

    with sqlite3.connect(database_path) as connection:
        response = connection.execute("SELECT response FROM subjects").fetchone()[0]

    assert response is None


def test_duplicate_sample_is_rejected(tmp_path: Path) -> None:
    rows = [sample_row(), sample_row(subject="sbj2")]
    csv_path = tmp_path / "cell-count.csv"
    write_csv(csv_path, rows)

    with pytest.raises(DataValidationError, match="duplicate sample"):
        build_database(
            csv_path,
            tmp_path / "cell-count.db",
            Path(__file__).parents[1] / "backend" / "schema.sql",
        )


def test_zero_total_cell_count_is_rejected(tmp_path: Path) -> None:
    row = sample_row(**{population: 0 for population in POPULATIONS})
    csv_path = tmp_path / "cell-count.csv"
    write_csv(csv_path, [row])

    with pytest.raises(DataValidationError, match="total cell count"):
        build_database(
            csv_path,
            tmp_path / "cell-count.db",
            Path(__file__).parents[1] / "backend" / "schema.sql",
        )


def test_replicate_samples_at_the_same_timepoint_are_allowed(tmp_path: Path) -> None:
    rows = [sample_row(), sample_row(sample="sample2")]

    database_path = build_test_database(tmp_path, rows)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 2
