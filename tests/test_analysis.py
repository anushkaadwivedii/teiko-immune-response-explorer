import pandas as pd
import pytest

from backend.analysis import _benjamini_hochberg, calculate_statistical_results


def test_benjamini_hochberg_adjustment() -> None:
    p_values = pd.Series([0.01, 0.04, 0.03, 0.002])

    adjusted = _benjamini_hochberg(p_values)

    assert adjusted.tolist() == pytest.approx([0.02, 0.04, 0.04, 0.008])


def test_statistics_report_all_populations() -> None:
    populations = [
        "b_cell",
        "cd8_t_cell",
        "cd4_t_cell",
        "nk_cell",
        "monocyte",
    ]
    rows = []
    for population in populations:
        for index, response in enumerate(["yes", "yes", "no", "no"]):
            rows.append(
                {
                    "subject": f"{population}-{index}",
                    "response": response,
                    "population": population,
                    "mean_percentage": 20 + index,
                }
            )

    results = calculate_statistical_results(pd.DataFrame(rows))

    assert results["population"].tolist() == populations
    assert set(results["responders_n"]) == {2}
    assert set(results["nonresponders_n"]) == {2}
    assert results["adjusted_p_value"].between(0, 1).all()
