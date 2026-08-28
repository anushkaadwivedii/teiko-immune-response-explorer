from fastapi.testclient import TestClient

from backend import api
from tests.test_load_data import build_test_database, sample_row


def test_vercel_entrypoint_exports_the_fastapi_app() -> None:
    from app import app

    assert app is api.app


def test_compiled_dashboard_is_served() -> None:
    client = TestClient(api.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Teiko Immune Response Explorer" in response.text


def test_overview_and_frequency_endpoints(tmp_path, monkeypatch) -> None:
    database_path = build_test_database(
        tmp_path,
        [
            sample_row(),
            sample_row(
                subject="sbj2",
                sample="sample2",
                response="no",
                b_cell=20,
            ),
        ],
    )
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)
    client = TestClient(api.app)

    overview = client.get("/api/overview")
    frequencies = client.get("/api/frequencies", params={"sample": "sample1"})

    assert overview.status_code == 200
    assert overview.json()["counts"] == {
        "projects": 1,
        "subjects": 2,
        "samples": 2,
        "cell_measurements": 10,
    }
    assert frequencies.status_code == 200
    assert frequencies.json()["total"] == 5
    assert sum(row["percentage"] for row in frequencies.json()["rows"]) == 100.0


def test_response_endpoint_uses_subject_level_values(tmp_path, monkeypatch) -> None:
    database_path = build_test_database(
        tmp_path,
        [
            sample_row(),
            sample_row(
                subject="sbj2",
                sample="sample2",
                response="no",
                b_cell=20,
            ),
        ],
    )
    monkeypatch.setattr(api, "DATABASE_PATH", database_path)
    client = TestClient(api.app)

    response = client.get("/api/response-analysis")

    assert response.status_code == 200
    assert response.json()["subject_count"] == 2
    assert len(response.json()["values"]) == 10
    assert len(response.json()["statistics"]) == 5
    assert len(response.json()["baseline_values"]) == 10
    assert len(response.json()["baseline_statistics"]) == 5
