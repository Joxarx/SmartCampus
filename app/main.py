# ============================================================
# main.py - Aplicación SmartCampus Services (FastAPI)
# Microservicio principal del sistema universitario
# ============================================================

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Literal, Optional, List
import os
import platform
import datetime
from datetime import timezone

# Instancia principal de la API
app = FastAPI(
    title="SmartCampus Services",
    description="API + Dashboard para gestión de servicios universitarios",
    version="1.2.0"
)

# CORS — abierto para demo. En producción restringir por dominio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_VERSION = os.getenv("APP_VERSION", "1.2.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============================================================
# ESTADO EN MEMORIA
# Nota: se reinicia cuando se redespliega el contenedor.
# Para persistencia real → SQLite con volumen, RDS o DynamoDB.
# ============================================================

_state = {
    "aulas": [
        {"id": "A-101", "edificio": "Edificio A", "tipo": "Aula", "capacidad": 40, "estado": "disponible", "equipamiento": ["proyector", "pizarra"]},
        {"id": "A-205", "edificio": "Edificio A", "tipo": "Aula", "capacidad": 35, "estado": "ocupada", "equipamiento": ["proyector"]},
        {"id": "B-301", "edificio": "Edificio B", "tipo": "Laboratorio de Cómputo", "capacidad": 30, "estado": "disponible", "equipamiento": ["30 PCs", "proyector", "aire acondicionado"]},
        {"id": "B-302", "edificio": "Edificio B", "tipo": "Laboratorio de Redes", "capacidad": 24, "estado": "mantenimiento", "equipamiento": ["routers Cisco", "switches"]},
        {"id": "C-110", "edificio": "Edificio C", "tipo": "Auditorio", "capacidad": 200, "estado": "disponible", "equipamiento": ["sonido", "proyector 4K", "tarima"]},
        {"id": "D-001", "edificio": "Edificio D", "tipo": "Sala de Estudio", "capacidad": 12, "estado": "ocupada", "equipamiento": ["pizarra", "TV"]},
    ],
    "eventos": [
        {"id": 1, "titulo": "Semana de la Ingeniería 2026",     "fecha": "2026-05-04", "hora": "09:00", "lugar": "Auditorio C-110", "categoria": "académico"},
        {"id": 2, "titulo": "Hackathon SmartCampus",              "fecha": "2026-05-15", "hora": "08:00", "lugar": "Lab B-301",       "categoria": "competencia"},
        {"id": 3, "titulo": "Conferencia: IA en la Educación",    "fecha": "2026-05-22", "hora": "16:00", "lugar": "Auditorio C-110", "categoria": "conferencia"},
        {"id": 4, "titulo": "Feria de Empleo 2026",               "fecha": "2026-06-02", "hora": "10:00", "lugar": "Plaza Central",   "categoria": "profesional"},
        {"id": 5, "titulo": "Taller de DevOps con AWS",           "fecha": "2026-06-10", "hora": "14:00", "lugar": "Lab B-301",       "categoria": "taller"},
    ],
    "horarios": [
        {"id": 1, "materia": "Cálculo Diferencial",   "profesor": "Dra. M. López",     "dia": "Lunes",     "hora": "07:00 - 09:00", "aula": "A-101"},
        {"id": 2, "materia": "Programación Web",      "profesor": "Ing. R. Pérez",     "dia": "Lunes",     "hora": "09:00 - 11:00", "aula": "B-301"},
        {"id": 3, "materia": "Bases de Datos",        "profesor": "Dr. J. Hernández",  "dia": "Martes",    "hora": "10:00 - 12:00", "aula": "B-301"},
        {"id": 4, "materia": "Redes de Computadoras", "profesor": "Mtro. A. Ramírez",  "dia": "Miércoles", "hora": "08:00 - 10:00", "aula": "B-302"},
        {"id": 5, "materia": "DevOps y Cloud",        "profesor": "Ing. J. Arias",     "dia": "Jueves",    "hora": "16:00 - 18:00", "aula": "B-301"},
        {"id": 6, "materia": "Inteligencia Artificial","profesor": "Dra. S. García",    "dia": "Viernes",   "hora": "11:00 - 13:00", "aula": "A-205"},
    ],
    "notificaciones": [
        {"id": 1, "tipo": "info",    "titulo": "Mantenimiento programado", "mensaje": "El sistema estará en mantenimiento el sábado 02:00-04:00.", "fecha": "2026-04-21"},
        {"id": 2, "tipo": "warning", "titulo": "Cambio de aula",            "mensaje": "La clase de DevOps del jueves se traslada al Lab B-302.",     "fecha": "2026-04-20"},
        {"id": 3, "tipo": "success", "titulo": "Inscripción abierta",        "mensaje": "Ya puedes inscribirte al Hackathon SmartCampus 2026.",         "fecha": "2026-04-19"},
        {"id": 4, "tipo": "danger",  "titulo": "Cierre temporal",            "mensaje": "El laboratorio B-302 estará cerrado por mantenimiento.",       "fecha": "2026-04-18"},
        {"id": 5, "tipo": "info",    "titulo": "Nuevo servicio",             "mensaje": "El sistema de notificaciones push ya está disponible.",        "fecha": "2026-04-17"},
    ],
}

_next_id = {
    "eventos": max((x["id"] for x in _state["eventos"]), default=0) + 1,
    "horarios": max((x["id"] for x in _state["horarios"]), default=0) + 1,
    "notificaciones": max((x["id"] for x in _state["notificaciones"]), default=0) + 1,
}


# ============================================================
# Pydantic models (entrada / actualización)
# ============================================================

EstadoAula = Literal["disponible", "ocupada", "mantenimiento"]
TipoNotificacion = Literal["info", "warning", "success", "danger"]


class AulaIn(BaseModel):
    edificio: str = Field(min_length=1, max_length=80)
    tipo: str = Field(min_length=1, max_length=80)
    capacidad: int = Field(gt=0, le=10_000)
    estado: EstadoAula
    equipamiento: List[str] = Field(default_factory=list)


class AulaCreate(AulaIn):
    id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9\-_.]+$")


class EventoIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    fecha: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    hora: str = Field(pattern=r"^\d{2}:\d{2}$")
    lugar: str = Field(min_length=1, max_length=200)
    categoria: str = Field(min_length=1, max_length=80)


class HorarioIn(BaseModel):
    materia: str = Field(min_length=1, max_length=120)
    profesor: str = Field(min_length=1, max_length=120)
    dia: str = Field(min_length=1, max_length=20)
    hora: str = Field(min_length=1, max_length=40)
    aula: str = Field(min_length=1, max_length=20)


class NotificacionIn(BaseModel):
    tipo: TipoNotificacion
    titulo: str = Field(min_length=1, max_length=200)
    mensaje: str = Field(min_length=1, max_length=500)
    fecha: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


# ============================================================
# Helpers
# ============================================================

def _find_idx(collection: str, item_id) -> int:
    for i, x in enumerate(_state[collection]):
        if x["id"] == item_id:
            return i
    raise HTTPException(status_code=404, detail=f"{collection[:-1]} '{item_id}' no encontrado")


# ============================================================
# UI / Health / Metadata
# ============================================================

@app.get("/ui", tags=["UI"], include_in_schema=False)
def serve_ui():
    """Sirve el dashboard HTML."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse(status_code=404, content={"error": "UI no disponible"})


@app.get("/dashboard", tags=["UI"], include_in_schema=False)
def dashboard_redirect():
    return RedirectResponse(url="/ui")


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "¡Bienvenido a SmartCampus Services!",
        "status": "online",
        "ui": "/ui",
        "docs": "/docs",
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", tags=["Health"])
def health_check():
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "version": APP_VERSION,
            "environment": ENVIRONMENT,
            "host": platform.node()
        }
    )


@app.get("/info", tags=["Sistema"])
def system_info():
    return {
        "app": "SmartCampus Services",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# Catálogo de servicios
# ============================================================

@app.get("/servicios", tags=["Servicios"])
def listar_servicios():
    servicios = [
        {"id": 1, "nombre": "Reservación de Aulas",         "descripcion": "Reserva salas y laboratorios del campus",         "endpoint": "/aulas",          "icono": "building", "activo": True},
        {"id": 2, "nombre": "Gestión de Eventos",           "descripcion": "Consulta y registro de eventos académicos",       "endpoint": "/eventos",        "icono": "calendar", "activo": True},
        {"id": 3, "nombre": "Consulta de Horarios",         "descripcion": "Visualiza horarios de clases y profesores",       "endpoint": "/horarios",       "icono": "clock",    "activo": True},
        {"id": 4, "nombre": "Notificaciones Institucionales","descripcion": "Sistema de alertas y comunicados oficiales",      "endpoint": "/notificaciones", "icono": "bell",     "activo": True},
    ]
    return {"total": len(servicios), "servicios": servicios}


# ============================================================
# AULAS (CRUD)
# ============================================================

@app.get("/aulas", tags=["Aulas"])
def listar_aulas():
    return {"total": len(_state["aulas"]), "aulas": _state["aulas"]}


@app.post("/aulas", tags=["Aulas"], status_code=status.HTTP_201_CREATED)
def crear_aula(payload: AulaCreate):
    if any(a["id"] == payload.id for a in _state["aulas"]):
        raise HTTPException(status_code=409, detail=f"Ya existe un aula con id '{payload.id}'")
    aula = payload.model_dump()
    _state["aulas"].append(aula)
    return aula


@app.put("/aulas/{aula_id}", tags=["Aulas"])
def actualizar_aula(aula_id: str, payload: AulaIn):
    idx = _find_idx("aulas", aula_id)
    aula = {"id": aula_id, **payload.model_dump()}
    _state["aulas"][idx] = aula
    return aula


@app.delete("/aulas/{aula_id}", tags=["Aulas"])
def eliminar_aula(aula_id: str):
    idx = _find_idx("aulas", aula_id)
    _state["aulas"].pop(idx)
    return {"deleted": aula_id}


# ============================================================
# EVENTOS (CRUD)
# ============================================================

@app.get("/eventos", tags=["Eventos"])
def listar_eventos():
    return {"total": len(_state["eventos"]), "eventos": _state["eventos"]}


@app.post("/eventos", tags=["Eventos"], status_code=status.HTTP_201_CREATED)
def crear_evento(payload: EventoIn):
    nuevo_id = _next_id["eventos"]
    _next_id["eventos"] += 1
    evento = {"id": nuevo_id, **payload.model_dump()}
    _state["eventos"].append(evento)
    return evento


@app.put("/eventos/{evento_id}", tags=["Eventos"])
def actualizar_evento(evento_id: int, payload: EventoIn):
    idx = _find_idx("eventos", evento_id)
    evento = {"id": evento_id, **payload.model_dump()}
    _state["eventos"][idx] = evento
    return evento


@app.delete("/eventos/{evento_id}", tags=["Eventos"])
def eliminar_evento(evento_id: int):
    idx = _find_idx("eventos", evento_id)
    _state["eventos"].pop(idx)
    return {"deleted": evento_id}


# ============================================================
# HORARIOS (CRUD)
# ============================================================

@app.get("/horarios", tags=["Horarios"])
def listar_horarios():
    return {"total": len(_state["horarios"]), "horarios": _state["horarios"]}


@app.post("/horarios", tags=["Horarios"], status_code=status.HTTP_201_CREATED)
def crear_horario(payload: HorarioIn):
    nuevo_id = _next_id["horarios"]
    _next_id["horarios"] += 1
    horario = {"id": nuevo_id, **payload.model_dump()}
    _state["horarios"].append(horario)
    return horario


@app.put("/horarios/{horario_id}", tags=["Horarios"])
def actualizar_horario(horario_id: int, payload: HorarioIn):
    idx = _find_idx("horarios", horario_id)
    horario = {"id": horario_id, **payload.model_dump()}
    _state["horarios"][idx] = horario
    return horario


@app.delete("/horarios/{horario_id}", tags=["Horarios"])
def eliminar_horario(horario_id: int):
    idx = _find_idx("horarios", horario_id)
    _state["horarios"].pop(idx)
    return {"deleted": horario_id}


# ============================================================
# NOTIFICACIONES (CRUD)
# ============================================================

@app.get("/notificaciones", tags=["Notificaciones"])
def listar_notificaciones():
    return {"total": len(_state["notificaciones"]), "notificaciones": _state["notificaciones"]}


@app.post("/notificaciones", tags=["Notificaciones"], status_code=status.HTTP_201_CREATED)
def crear_notificacion(payload: NotificacionIn):
    nuevo_id = _next_id["notificaciones"]
    _next_id["notificaciones"] += 1
    fecha = payload.fecha or datetime.datetime.now(timezone.utc).date().isoformat()
    notif = {"id": nuevo_id, "tipo": payload.tipo, "titulo": payload.titulo, "mensaje": payload.mensaje, "fecha": fecha}
    _state["notificaciones"].append(notif)
    return notif


@app.put("/notificaciones/{notif_id}", tags=["Notificaciones"])
def actualizar_notificacion(notif_id: int, payload: NotificacionIn):
    idx = _find_idx("notificaciones", notif_id)
    fecha = payload.fecha or _state["notificaciones"][idx].get("fecha")
    notif = {"id": notif_id, "tipo": payload.tipo, "titulo": payload.titulo, "mensaje": payload.mensaje, "fecha": fecha}
    _state["notificaciones"][idx] = notif
    return notif


@app.delete("/notificaciones/{notif_id}", tags=["Notificaciones"])
def eliminar_notificacion(notif_id: int):
    idx = _find_idx("notificaciones", notif_id)
    _state["notificaciones"].pop(idx)
    return {"deleted": notif_id}
