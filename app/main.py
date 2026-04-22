# ============================================================
# main.py - Aplicación SmartCampus Services (FastAPI)
# Microservicio principal del sistema universitario
# ============================================================

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import platform
import datetime
from datetime import timezone

# Instancia principal de la API
app = FastAPI(
    title="SmartCampus Services",
    description="API + Dashboard para gestión de servicios universitarios",
    version="1.1.0"
)

# CORS — permitimos cualquier origen (apto para demo / dev).
# En producción real esto debería restringirse a dominios concretos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno para configuración dinámica
APP_VERSION = os.getenv("APP_VERSION", "1.1.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Resolución de la carpeta static relativa a este archivo
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

# Servimos archivos estáticos (CSS, JS, imágenes) en /static
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ============================================================
# DASHBOARD (UI)
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
    """Atajo: /dashboard → /ui"""
    return RedirectResponse(url="/ui")


# ============================================================
# HEALTH & METADATA
# ============================================================

@app.get("/", tags=["Health"])
def root():
    """Endpoint raíz - Mensaje de bienvenida del sistema."""
    return {
        "message": "¡Bienvenido a SmartCampus Services!",
        "status": "online",
        "ui": "/ui",
        "docs": "/docs",
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check para Kubernetes / Docker / load balancer.
    Si retorna 200, el contenedor permanece en servicio.
    """
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
    """Información del sistema - útil para depuración."""
    return {
        "app": "SmartCampus Services",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }


# ============================================================
# SERVICIOS
# ============================================================

@app.get("/servicios", tags=["Servicios"])
def listar_servicios():
    """Lista todos los servicios universitarios disponibles."""
    servicios = [
        {
            "id": 1,
            "nombre": "Reservación de Aulas",
            "descripcion": "Reserva salas y laboratorios del campus",
            "endpoint": "/aulas",
            "icono": "building",
            "activo": True
        },
        {
            "id": 2,
            "nombre": "Gestión de Eventos",
            "descripcion": "Consulta y registro de eventos académicos",
            "endpoint": "/eventos",
            "icono": "calendar",
            "activo": True
        },
        {
            "id": 3,
            "nombre": "Consulta de Horarios",
            "descripcion": "Visualiza horarios de clases y profesores",
            "endpoint": "/horarios",
            "icono": "clock",
            "activo": True
        },
        {
            "id": 4,
            "nombre": "Notificaciones Institucionales",
            "descripcion": "Sistema de alertas y comunicados oficiales",
            "endpoint": "/notificaciones",
            "icono": "bell",
            "activo": True
        }
    ]
    return {"total": len(servicios), "servicios": servicios}


# ============================================================
# AULAS — Reservación de aulas (datos de demostración)
# ============================================================

@app.get("/aulas", tags=["Aulas"])
def listar_aulas():
    """Lista las aulas y laboratorios del campus con su estado actual."""
    aulas = [
        {"id": "A-101", "edificio": "Edificio A", "tipo": "Aula", "capacidad": 40, "estado": "disponible", "equipamiento": ["proyector", "pizarra"]},
        {"id": "A-205", "edificio": "Edificio A", "tipo": "Aula", "capacidad": 35, "estado": "ocupada", "equipamiento": ["proyector"]},
        {"id": "B-301", "edificio": "Edificio B", "tipo": "Laboratorio de Cómputo", "capacidad": 30, "estado": "disponible", "equipamiento": ["30 PCs", "proyector", "aire acondicionado"]},
        {"id": "B-302", "edificio": "Edificio B", "tipo": "Laboratorio de Redes", "capacidad": 24, "estado": "mantenimiento", "equipamiento": ["routers Cisco", "switches"]},
        {"id": "C-110", "edificio": "Edificio C", "tipo": "Auditorio", "capacidad": 200, "estado": "disponible", "equipamiento": ["sonido", "proyector 4K", "tarima"]},
        {"id": "D-001", "edificio": "Edificio D", "tipo": "Sala de Estudio", "capacidad": 12, "estado": "ocupada", "equipamiento": ["pizarra", "TV"]},
    ]
    return {"total": len(aulas), "aulas": aulas}


# ============================================================
# EVENTOS — Eventos académicos
# ============================================================

@app.get("/eventos", tags=["Eventos"])
def listar_eventos():
    """Lista los próximos eventos académicos."""
    eventos = [
        {"id": 1, "titulo": "Semana de la Ingeniería 2026", "fecha": "2026-05-04", "hora": "09:00", "lugar": "Auditorio C-110", "categoria": "académico"},
        {"id": 2, "titulo": "Hackathon SmartCampus", "fecha": "2026-05-15", "hora": "08:00", "lugar": "Lab B-301", "categoria": "competencia"},
        {"id": 3, "titulo": "Conferencia: IA en la Educación", "fecha": "2026-05-22", "hora": "16:00", "lugar": "Auditorio C-110", "categoria": "conferencia"},
        {"id": 4, "titulo": "Feria de Empleo 2026", "fecha": "2026-06-02", "hora": "10:00", "lugar": "Plaza Central", "categoria": "profesional"},
        {"id": 5, "titulo": "Taller de DevOps con AWS", "fecha": "2026-06-10", "hora": "14:00", "lugar": "Lab B-301", "categoria": "taller"},
    ]
    return {"total": len(eventos), "eventos": eventos}


# ============================================================
# HORARIOS — Horarios de clases
# ============================================================

@app.get("/horarios", tags=["Horarios"])
def listar_horarios():
    """Lista horarios de clases representativos."""
    horarios = [
        {"id": 1, "materia": "Cálculo Diferencial", "profesor": "Dra. M. López", "dia": "Lunes", "hora": "07:00 - 09:00", "aula": "A-101"},
        {"id": 2, "materia": "Programación Web", "profesor": "Ing. R. Pérez", "dia": "Lunes", "hora": "09:00 - 11:00", "aula": "B-301"},
        {"id": 3, "materia": "Bases de Datos", "profesor": "Dr. J. Hernández", "dia": "Martes", "hora": "10:00 - 12:00", "aula": "B-301"},
        {"id": 4, "materia": "Redes de Computadoras", "profesor": "Mtro. A. Ramírez", "dia": "Miércoles", "hora": "08:00 - 10:00", "aula": "B-302"},
        {"id": 5, "materia": "DevOps y Cloud", "profesor": "Ing. J. Arias", "dia": "Jueves", "hora": "16:00 - 18:00", "aula": "B-301"},
        {"id": 6, "materia": "Inteligencia Artificial", "profesor": "Dra. S. García", "dia": "Viernes", "hora": "11:00 - 13:00", "aula": "A-205"},
    ]
    return {"total": len(horarios), "horarios": horarios}


# ============================================================
# NOTIFICACIONES — Comunicados institucionales
# ============================================================

@app.get("/notificaciones", tags=["Notificaciones"])
def listar_notificaciones():
    """Lista notificaciones recientes del sistema."""
    notificaciones = [
        {"id": 1, "tipo": "info",      "titulo": "Mantenimiento programado", "mensaje": "El sistema estará en mantenimiento el sábado 02:00-04:00.", "fecha": "2026-04-21"},
        {"id": 2, "tipo": "warning",   "titulo": "Cambio de aula",            "mensaje": "La clase de DevOps del jueves se traslada al Lab B-302.",     "fecha": "2026-04-20"},
        {"id": 3, "tipo": "success",   "titulo": "Inscripción abierta",        "mensaje": "Ya puedes inscribirte al Hackathon SmartCampus 2026.",         "fecha": "2026-04-19"},
        {"id": 4, "tipo": "danger",    "titulo": "Cierre temporal",            "mensaje": "El laboratorio B-302 estará cerrado por mantenimiento.",       "fecha": "2026-04-18"},
        {"id": 5, "tipo": "info",      "titulo": "Nuevo servicio",             "mensaje": "El sistema de notificaciones push ya está disponible.",        "fecha": "2026-04-17"},
    ]
    return {"total": len(notificaciones), "notificaciones": notificaciones}
