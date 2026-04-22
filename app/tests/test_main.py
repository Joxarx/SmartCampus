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


# ─── CRUD: AULAS ────────────────────────────────────────────

def test_aula_crud_lifecycle():
    nueva = {
        "id": "TEST-999",
        "edificio": "Edificio Test",
        "tipo": "Sala de Pruebas",
        "capacidad": 5,
        "estado": "disponible",
        "equipamiento": ["pizarra"],
    }
    # Create
    r = client.post("/aulas", json=nueva)
    assert r.status_code == 201
    assert r.json()["id"] == "TEST-999"

    # Conflict on duplicate
    r2 = client.post("/aulas", json=nueva)
    assert r2.status_code == 409

    # Update
    actualizada = {**nueva, "estado": "ocupada", "capacidad": 8}
    actualizada.pop("id")
    r3 = client.put("/aulas/TEST-999", json=actualizada)
    assert r3.status_code == 200
    assert r3.json()["estado"] == "ocupada"
    assert r3.json()["capacidad"] == 8

    # Delete
    r4 = client.delete("/aulas/TEST-999")
    assert r4.status_code == 200

    # 404 después de borrar
    r5 = client.put("/aulas/TEST-999", json=actualizada)
    assert r5.status_code == 404


def test_aula_validation_rejects_invalid_estado():
    bad = {
        "id": "BAD-001",
        "edificio": "X",
        "tipo": "X",
        "capacidad": 10,
        "estado": "inventado",
        "equipamiento": [],
    }
    r = client.post("/aulas", json=bad)
    assert r.status_code == 422


# ─── CRUD: EVENTOS ──────────────────────────────────────────

def test_evento_create_update_delete():
    payload = {
        "titulo": "Evento de prueba",
        "fecha": "2026-12-31",
        "hora": "23:59",
        "lugar": "Lugar de prueba",
        "categoria": "test",
    }
    r = client.post("/eventos", json=payload)
    assert r.status_code == 201
    eid = r.json()["id"]

    r2 = client.put(f"/eventos/{eid}", json={**payload, "titulo": "Renombrado"})
    assert r2.status_code == 200
    assert r2.json()["titulo"] == "Renombrado"

    r3 = client.delete(f"/eventos/{eid}")
    assert r3.status_code == 200
    assert r3.json()["deleted"] == eid


# ─── CRUD: NOTIFICACIONES ───────────────────────────────────

def test_notificacion_create_autofecha():
    payload = {"tipo": "info", "titulo": "Prueba", "mensaje": "msg"}
    r = client.post("/notificaciones", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["fecha"]  # auto-asignada
    # Cleanup
    client.delete(f"/notificaciones/{body['id']}")
