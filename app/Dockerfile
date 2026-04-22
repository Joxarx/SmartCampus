# ============================================================
# Dockerfile - Imagen optimizada para SmartCampus Services
# Técnica: Multi-stage build para minimizar el tamaño final
# ============================================================

# ── ETAPA 1: Builder ────────────────────────────────────────
# Usamos una imagen completa para instalar dependencias
FROM python:3.11-slim AS builder

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos SOLO requirements.txt primero.
# Docker cachea esta capa: si no cambian las deps, no reinstala.
# Esto acelera enormemente las builds repetidas en CI/CD.
COPY requirements.txt .

# Instalamos dependencias en un directorio local (no en el sistema)
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── ETAPA 2: Runtime ─────────────────────────────────────────
# Imagen final mínima: solo lo necesario para ejecutar la app
FROM python:3.11-slim AS runtime

# Metadatos de la imagen (buena práctica OCI)
LABEL maintainer="Joshua Arias <Al03043935>"
LABEL project="SmartCampus Services"
LABEL version="1.0.0"

# Variables de entorno predeterminadas
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_VERSION="1.0.0" \
    ENVIRONMENT="production"

WORKDIR /app

# Copiamos las dependencias instaladas desde la etapa builder
COPY --from=builder /install /usr/local

# Copiamos el código fuente de la aplicación
COPY . .

# Creamos un usuario no-root por seguridad.
# Nunca ejecutar contenedores como root en producción.
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Documentamos el puerto que expone la aplicación
EXPOSE 8000

# Health check interno del contenedor
# Docker verifica cada 30s si la app responde correctamente
# Valida explícitamente status 200 - si la app responde 4xx/5xx falla
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8000/health',timeout=4); sys.exit(0 if r.status==200 else 1)"

# Comando de inicio: servidor Uvicorn con recarga en dev
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
