# ============================================================
# main.py - Aplicación SmartCampus Services (FastAPI)
# Microservicio principal del sistema universitario
# ============================================================

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import platform
import datetime

# Instancia principal de la API
app = FastAPI(
    title="SmartCampus Services",
    description="API para gestión de servicios universitarios",
    version="1.0.0"
)

# Variables de entorno para configuración dinámica
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@app.get("/", tags=["Health"])
def root():
    """Endpoint raíz - Mensaje de bienvenida del sistema."""
    return {
        "message": "¡Bienvenido a SmartCampus Services!",
        "status": "online",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check para Kubernetes.
    K8s llama a este endpoint para saber si el pod está saludable.
    Si retorna 200, el pod permanece en servicio.
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


@app.get("/servicios", tags=["Servicios"])
def listar_servicios():
    """Lista todos los servicios universitarios disponibles."""
    servicios = [
        {
            "id": 1,
            "nombre": "Reservación de Aulas",
            "descripcion": "Reserva salas y laboratorios del campus",
            "activo": True
        },
        {
            "id": 2,
            "nombre": "Gestión de Eventos",
            "descripcion": "Consulta y registro de eventos académicos",
            "activo": True
        },
        {
            "id": 3,
            "nombre": "Consulta de Horarios",
            "descripcion": "Visualiza horarios de clases y profesores",
            "activo": True
        },
        {
            "id": 4,
            "nombre": "Notificaciones Institucionales",
            "descripcion": "Sistema de alertas y comunicados oficiales",
            "activo": True
        }
    ]
    return {"total": len(servicios), "servicios": servicios}


@app.get("/info", tags=["Sistema"])
def system_info():
    """Información del sistema - útil para depuración en K8s."""
    return {
        "app": "SmartCampus Services",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
