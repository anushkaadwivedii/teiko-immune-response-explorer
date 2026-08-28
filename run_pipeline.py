from pathlib import Path

from backend.analysis import run_analysis


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = ROOT / "cell-count.db"
OUTPUT_DIR = ROOT / "outputs"


def main() -> None:
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            "cell-count.db is missing. Run `python load_data.py` first."
        )

    summary = run_analysis(DATABASE_PATH, OUTPUT_DIR)
    print(f"Generated analysis outputs in {OUTPUT_DIR.name}/")
    print(
        "Baseline average B-cell count for melanoma male responders: "
        f"{summary['average_b_cells_melanoma_male_responders_time_0']:.2f}"
    )


if __name__ == "__main__":
    main()
