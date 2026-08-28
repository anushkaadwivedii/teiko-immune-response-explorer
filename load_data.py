from pathlib import Path

from backend.database import build_database


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cell-count.csv"
DATABASE_PATH = ROOT / "cell-count.db"
SCHEMA_PATH = ROOT / "backend" / "schema.sql"


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Input file not found: {CSV_PATH}")

    build_database(CSV_PATH, DATABASE_PATH, SCHEMA_PATH)
    print(f"Loaded {CSV_PATH.name} into {DATABASE_PATH.name}")


if __name__ == "__main__":
    main()
