from __future__ import annotations

import csv
import os
import sqlite3
from pathlib import Path
from typing import Iterable


POPULATIONS = (
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
)

METADATA_COLUMNS = (
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
)

EXPECTED_COLUMNS = METADATA_COLUMNS + POPULATIONS


class DataValidationError(ValueError):
    """Raised when the source file cannot be loaded safely."""


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise DataValidationError(
                "Unexpected CSV columns. Expected: " + ", ".join(EXPECTED_COLUMNS)
            )
        rows = list(reader)

    if not rows:
        raise DataValidationError("The source CSV contains no data rows.")
    return rows


def _required_text(row: dict[str, str], column: str, row_number: int) -> str:
    value = row[column].strip()
    if not value:
        raise DataValidationError(f"Row {row_number}: {column} is required.")
    return value


def _nonnegative_int(row: dict[str, str], column: str, row_number: int) -> int:
    raw_value = _required_text(row, column, row_number)
    try:
        value = int(raw_value)
    except ValueError as error:
        raise DataValidationError(
            f"Row {row_number}: {column} must be an integer."
        ) from error
    if value < 0:
        raise DataValidationError(f"Row {row_number}: {column} cannot be negative.")
    return value


def _validated_rows(
    rows: Iterable[dict[str, str]],
) -> list[dict[str, object]]:
    validated: list[dict[str, object]] = []
    sample_codes: set[str] = set()
    subject_metadata: dict[tuple[str, str], tuple[object, ...]] = {}

    for row_number, row in enumerate(rows, start=2):
        project = _required_text(row, "project", row_number)
        subject = _required_text(row, "subject", row_number)
        sample = _required_text(row, "sample", row_number)
        response = row["response"].strip() or None

        if response not in {None, "yes", "no"}:
            raise DataValidationError(
                f"Row {row_number}: response must be yes, no, or blank."
            )
        if sample in sample_codes:
            raise DataValidationError(
                f"Row {row_number}: duplicate sample identifier {sample}."
            )
        sample_codes.add(sample)

        age = _nonnegative_int(row, "age", row_number)
        if age > 130:
            raise DataValidationError(f"Row {row_number}: age must be 130 or less.")

        sex = _required_text(row, "sex", row_number)
        if sex not in {"M", "F"}:
            raise DataValidationError(f"Row {row_number}: sex must be M or F.")

        metadata = (
            _required_text(row, "condition", row_number),
            age,
            sex,
            _required_text(row, "treatment", row_number),
            response,
        )
        subject_key = (project, subject)
        previous_metadata = subject_metadata.setdefault(subject_key, metadata)
        if previous_metadata != metadata:
            raise DataValidationError(
                f"Row {row_number}: metadata changed for subject {subject}."
            )

        counts = tuple(
            _nonnegative_int(row, population, row_number)
            for population in POPULATIONS
        )
        if sum(counts) == 0:
            raise DataValidationError(
                f"Row {row_number}: total cell count must be greater than zero."
            )

        validated.append(
            {
                "project": project,
                "subject": subject,
                "condition": metadata[0],
                "age": age,
                "sex": sex,
                "treatment": metadata[3],
                "response": response,
                "sample": sample,
                "sample_type": _required_text(row, "sample_type", row_number),
                "time": _nonnegative_int(
                    row, "time_from_treatment_start", row_number
                ),
                "counts": counts,
            }
        )

    return validated


def _create_schema(connection: sqlite3.Connection, schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))


def _load_rows(
    connection: sqlite3.Connection, rows: list[dict[str, object]]
) -> None:
    project_codes = sorted({str(row["project"]) for row in rows})
    connection.executemany(
        "INSERT INTO projects (project_code) VALUES (?)",
        ((code,) for code in project_codes),
    )
    connection.executemany(
        "INSERT INTO cell_populations (population_name) VALUES (?)",
        ((population,) for population in POPULATIONS),
    )

    project_ids = dict(
        connection.execute("SELECT project_code, project_id FROM projects")
    )
    subject_rows: dict[tuple[str, str], tuple[object, ...]] = {}
    for row in rows:
        key = (str(row["project"]), str(row["subject"]))
        subject_rows[key] = (
            project_ids[key[0]],
            key[1],
            row["condition"],
            row["age"],
            row["sex"],
            row["treatment"],
            row["response"],
        )

    connection.executemany(
        """
        INSERT INTO subjects (
            project_id, subject_code, condition, age, sex, treatment, response
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        subject_rows.values(),
    )
    subject_ids = {
        (project_code, subject_code): subject_id
        for project_code, subject_code, subject_id in connection.execute(
            """
            SELECT p.project_code, s.subject_code, s.subject_id
            FROM subjects AS s
            JOIN projects AS p ON p.project_id = s.project_id
            """
        )
    }

    sample_records = [
        (
            row["sample"],
            subject_ids[(str(row["project"]), str(row["subject"]))],
            row["sample_type"],
            row["time"],
        )
        for row in rows
    ]
    connection.executemany(
        """
        INSERT INTO samples (
            sample_code, subject_id, sample_type, time_from_treatment_start
        ) VALUES (?, ?, ?, ?)
        """,
        sample_records,
    )
    sample_ids = dict(
        connection.execute("SELECT sample_code, sample_id FROM samples")
    )
    population_ids = dict(
        connection.execute(
            "SELECT population_name, population_id FROM cell_populations"
        )
    )
    count_records = (
        (sample_ids[str(row["sample"])], population_ids[population], count)
        for row in rows
        for population, count in zip(POPULATIONS, row["counts"], strict=True)
    )
    connection.executemany(
        """
        INSERT INTO cell_counts (sample_id, population_id, cell_count)
        VALUES (?, ?, ?)
        """,
        count_records,
    )
    connection.execute("PRAGMA optimize")


def build_database(csv_path: Path, database_path: Path, schema_path: Path) -> None:
    rows = _validated_rows(_read_rows(csv_path))
    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")

    if temporary_path.exists():
        temporary_path.unlink()

    try:
        with sqlite3.connect(temporary_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            _create_schema(connection, schema_path)
            _load_rows(connection, rows)
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise DataValidationError(
                    f"Foreign key validation failed: {violations[:5]}"
                )
        os.replace(temporary_path, database_path)
    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise
