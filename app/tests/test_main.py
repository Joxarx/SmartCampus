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


def test_aulas_returns_list():
    response = client.get("/aulas")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(data["aulas"])
    assert data["total"] > 0
    for aula in data["aulas"]:
        assert "id" in aula
        assert "estado" in aula
        assert aula["estado"] in {"disponible", "ocupada", "mantenimiento"}


def test_eventos_returns_list():
    response = client.get("/eventos")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(data["eventos"])
    assert data["total"] > 0
    for evento in data["eventos"]:
        assert "titulo" in evento
        assert "fecha" in evento


def test_horarios_returns_list():
    response = client.get("/horarios")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(data["horarios"])
    for horario in data["horarios"]:
        assert "materia" in horario
        assert "profesor" in horario
        assert "aula" in horario


def test_notificaciones_returns_list():
    response = client.get("/notificaciones")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == len(data["notificaciones"])
    for notif in data["notificaciones"]:
        assert notif["tipo"] in {"info", "warning", "success", "danger"}
