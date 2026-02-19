from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_returns_welcome():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "timestamp" in data


def test_health_check_returns_healthy():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_servicios_returns_four_services():
    response = client.get("/servicios")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["servicios"]) == 4
    for servicio in data["servicios"]:
        assert servicio["activo"] is True


def test_info_returns_system_details():
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "SmartCampus Services"
    assert "version" in data
    assert "environment" in data
    assert "python_version" in data
    assert "timestamp" in data
