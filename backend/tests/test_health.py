from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ritacart.db'}")

    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert (tmp_path / "ritacart.db").is_file()
    assert (tmp_path / "receipts").is_dir()
