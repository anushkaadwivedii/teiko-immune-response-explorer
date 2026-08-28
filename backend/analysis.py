from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy.stats import mannwhitneyu


POPULATION_ORDER = [
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte",
]

DISPLAY_NAMES = {
    "b_cell": "B cell",
    "cd8_t_cell": "CD8 T cell",
    "cd4_t_cell": "CD4 T cell",
    "nk_cell": "NK cell",
    "monocyte": "Monocyte",
}


def _benjamini_hochberg(p_values: pd.Series) -> pd.Series:
    """Adjust p-values while preserving their original order."""
    total = len(p_values)
    ordered = p_values.sort_values()
    adjusted = pd.Series(index=ordered.index, dtype=float)
    running_minimum = 1.0

    for reverse_rank, (index, p_value) in enumerate(
        reversed(list(ordered.items())), start=1
    ):
        rank = total - reverse_rank + 1
        running_minimum = min(running_minimum, p_value * total / rank)
        adjusted.loc[index] = min(running_minimum, 1.0)

    return adjusted.reindex(p_values.index)


def export_frequency_table(
    connection: sqlite3.Connection, output_dir: Path
) -> pd.DataFrame:
    frequencies = pd.read_sql_query(
        """
        SELECT sample, total_count, population, count, percentage
        FROM sample_population_frequencies
        ORDER BY sample, population
        """,
        connection,
    )
    frequencies.to_csv(output_dir / "sample_frequencies.csv", index=False)
    return frequencies


def response_analysis_values(
    connection: sqlite3.Connection,
    time_from_treatment_start: int | None = None,
) -> pd.DataFrame:
    time_filter = ""
    parameters: list[object] = []
    if time_from_treatment_start is not None:
        time_filter = "AND s.time_from_treatment_start = ?"
        parameters.append(time_from_treatment_start)

    sample_values = pd.read_sql_query(
        f"""
        SELECT
            sub.subject_id AS subject_key,
            p.project_code AS project,
            sub.subject_code AS subject,
            sub.response,
            f.population,
            f.percentage
        FROM sample_population_frequencies AS f
        JOIN samples AS s ON s.sample_code = f.sample
        JOIN subjects AS sub ON sub.subject_id = s.subject_id
        JOIN projects AS p ON p.project_id = sub.project_id
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND sub.response IN ('yes', 'no')
          {time_filter}
        """,
        connection,
        params=parameters,
    )

    return (
        sample_values.groupby(
            ["subject_key", "project", "subject", "response", "population"],
            as_index=False,
        )["percentage"]
        .mean()
        .rename(columns={"percentage": "mean_percentage"})
    )


def calculate_statistical_results(subject_values: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for population in POPULATION_ORDER:
        population_values = subject_values.loc[
            subject_values["population"] == population
        ]
        responders = population_values.loc[
            population_values["response"] == "yes", "mean_percentage"
        ]
        nonresponders = population_values.loc[
            population_values["response"] == "no", "mean_percentage"
        ]

        test = mannwhitneyu(
            responders,
            nonresponders,
            alternative="two-sided",
            method="asymptotic",
        )
        effect_size = 2 * test.statistic / (len(responders) * len(nonresponders)) - 1

        responder_median = float(responders.median())
        nonresponder_median = float(nonresponders.median())
        rows.append(
            {
                "population": population,
                "responders_n": len(responders),
                "nonresponders_n": len(nonresponders),
                "responder_median_percentage": responder_median,
                "nonresponder_median_percentage": nonresponder_median,
                "median_difference_percentage_points": (
                    responder_median - nonresponder_median
                ),
                "mann_whitney_u": float(test.statistic),
                "p_value": float(test.pvalue),
                "rank_biserial_effect_size": float(effect_size),
            }
        )

    results = pd.DataFrame(rows)
    results["adjusted_p_value"] = _benjamini_hochberg(results["p_value"])
    results["nominally_significant_at_0_05"] = results["p_value"] < 0.05
    results["fdr_significant_at_0_05"] = results["adjusted_p_value"] < 0.05
    return results


def save_response_boxplots(
    subject_values: pd.DataFrame,
    output_path: Path,
    subtitle: str,
) -> None:
    plot_data = subject_values.copy()
    plot_data["population"] = plot_data["population"].map(DISPLAY_NAMES)
    plot_data["response"] = plot_data["response"].map(
        {"yes": "Responder", "no": "Nonresponder"}
    )

    sns.set_theme(style="whitegrid", context="notebook")
    figure, axes = plt.subplots(1, 5, figsize=(18, 5), sharey=True)
    palette = {"Responder": "#0E7490", "Nonresponder": "#D97706"}

    for axis, population in zip(axes, POPULATION_ORDER, strict=True):
        display_name = DISPLAY_NAMES[population]
        values = plot_data.loc[plot_data["population"] == display_name]
        sns.boxplot(
            data=values,
            x="response",
            y="mean_percentage",
            hue="response",
            order=["Responder", "Nonresponder"],
            palette=palette,
            legend=False,
            width=0.6,
            fliersize=2,
            ax=axis,
        )
        axis.set_title(display_name)
        axis.set_xlabel("")
        axis.tick_params(axis="x", rotation=25)
        axis.set_ylabel(
            "Subject mean relative frequency (%)" if axis is axes[0] else ""
        )

    figure.suptitle(
        "Immune cell frequencies by miraclib response",
        fontsize=16,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.01,
        subtitle,
        ha="center",
        fontsize=10,
    )
    figure.supxlabel("Treatment response", y=0.06, fontsize=11)
    figure.tight_layout(rect=(0, 0.09, 1, 0.93))
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def export_response_analysis(
    connection: sqlite3.Connection, output_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subject_values = response_analysis_values(connection)
    statistical_results = calculate_statistical_results(subject_values)
    baseline_values = response_analysis_values(connection, time_from_treatment_start=0)
    baseline_statistics = calculate_statistical_results(baseline_values)

    subject_values.to_csv(output_dir / "response_analysis_values.csv", index=False)
    statistical_results.to_csv(
        output_dir / "statistical_results.csv", index=False
    )
    baseline_values.to_csv(
        output_dir / "baseline_response_analysis_values.csv", index=False
    )
    baseline_statistics.to_csv(
        output_dir / "baseline_predictive_statistics.csv", index=False
    )
    save_response_boxplots(
        subject_values,
        output_dir / "response_boxplots.png",
        "Melanoma PBMC samples; each subject is represented by the mean of days 0, 7, and 14",
    )
    save_response_boxplots(
        baseline_values,
        output_dir / "baseline_response_boxplots.png",
        "Melanoma PBMC samples at day 0; one value per subject",
    )
    return subject_values, statistical_results, baseline_values, baseline_statistics


def export_baseline_analysis(
    connection: sqlite3.Connection, output_dir: Path
) -> dict[str, object]:
    baseline_samples = pd.read_sql_query(
        """
        SELECT
            p.project_code AS project,
            sub.subject_code AS subject,
            sub.response,
            sub.sex,
            s.sample_code AS sample
        FROM samples AS s
        JOIN subjects AS sub ON sub.subject_id = s.subject_id
        JOIN projects AS p ON p.project_id = sub.project_id
        WHERE sub.condition = 'melanoma'
          AND sub.treatment = 'miraclib'
          AND s.sample_type = 'PBMC'
          AND s.time_from_treatment_start = 0
        ORDER BY p.project_code, sub.subject_code
        """,
        connection,
    )
    baseline_samples.to_csv(output_dir / "baseline_samples.csv", index=False)

    samples_by_project = (
        baseline_samples.groupby("project", as_index=False)
        .size()
        .rename(columns={"size": "sample_count"})
    )
    subjects_by_response = (
        baseline_samples[["project", "subject", "response"]]
        .drop_duplicates()
        .groupby("response", as_index=False)
        .size()
        .rename(columns={"size": "subject_count"})
    )
    subjects_by_sex = (
        baseline_samples[["project", "subject", "sex"]]
        .drop_duplicates()
        .groupby("sex", as_index=False)
        .size()
        .rename(columns={"size": "subject_count"})
    )

    samples_by_project.to_csv(
        output_dir / "baseline_samples_by_project.csv", index=False
    )
    subjects_by_response.to_csv(
        output_dir / "baseline_subjects_by_response.csv", index=False
    )
    subjects_by_sex.to_csv(
        output_dir / "baseline_subjects_by_sex.csv", index=False
    )

    average_b_cell = connection.execute(
        """
        SELECT AVG(cc.cell_count)
        FROM cell_counts AS cc
        JOIN cell_populations AS pop ON pop.population_id = cc.population_id
        JOIN samples AS s ON s.sample_id = cc.sample_id
        JOIN subjects AS sub ON sub.subject_id = s.subject_id
        WHERE pop.population_name = 'b_cell'
          AND sub.condition = 'melanoma'
          AND sub.sex = 'M'
          AND sub.response = 'yes'
          AND s.time_from_treatment_start = 0
        """
    ).fetchone()[0]

    summary = {
        "baseline_sample_count": int(len(baseline_samples)),
        "baseline_subject_count": int(
            baseline_samples[["project", "subject"]].drop_duplicates().shape[0]
        ),
        "samples_by_project": dict(
            samples_by_project.itertuples(index=False, name=None)
        ),
        "subjects_by_response": dict(
            subjects_by_response.itertuples(index=False, name=None)
        ),
        "subjects_by_sex": dict(subjects_by_sex.itertuples(index=False, name=None)),
        "average_b_cells_melanoma_male_responders_time_0": round(
            float(average_b_cell), 2
        ),
    }
    (output_dir / "baseline_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def run_analysis(database_path: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        frequencies = export_frequency_table(connection, output_dir)
        subject_values, statistics, baseline_values, baseline_statistics = (
            export_response_analysis(connection, output_dir)
        )
        baseline_summary = export_baseline_analysis(connection, output_dir)

    strongest_signal = statistics.sort_values("p_value").iloc[0]
    strongest_baseline_signal = baseline_statistics.sort_values("p_value").iloc[0]

    summary = {
        "frequency_rows": int(len(frequencies)),
        "response_analysis_subjects": int(subject_values["subject_key"].nunique()),
        "significant_populations": statistics.loc[
            statistics["fdr_significant_at_0_05"], "population"
        ].tolist(),
        "response_signal": {
            "population": strongest_signal["population"],
            "median_difference_percentage_points": float(
                strongest_signal["median_difference_percentage_points"]
            ),
            "p_value": float(strongest_signal["p_value"]),
            "adjusted_p_value": float(strongest_signal["adjusted_p_value"]),
            "fdr_significant": bool(
                strongest_signal["fdr_significant_at_0_05"]
            ),
        },
        "baseline_response_analysis_subjects": int(
            baseline_values["subject_key"].nunique()
        ),
        "baseline_significant_populations": baseline_statistics.loc[
            baseline_statistics["fdr_significant_at_0_05"], "population"
        ].tolist(),
        "baseline_response_signal": {
            "population": strongest_baseline_signal["population"],
            "median_difference_percentage_points": float(
                strongest_baseline_signal["median_difference_percentage_points"]
            ),
            "p_value": float(strongest_baseline_signal["p_value"]),
            "adjusted_p_value": float(
                strongest_baseline_signal["adjusted_p_value"]
            ),
            "fdr_significant": bool(
                strongest_baseline_signal["fdr_significant_at_0_05"]
            ),
        },
        **baseline_summary,
    }
    (output_dir / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary
