# 🎓 SmartCampus Services — Proyecto Integrador DevOps

<p align="center">
  <img src="https://img.shields.io/badge/DevOps-Pipeline-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/Kubernetes-EKS-326CE5?style=for-the-badge&logo=kubernetes" />
  <img src="https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform" />
  <img src="https://img.shields.io/badge/Helm-Chart-0F1689?style=for-the-badge&logo=helm" />
</p>

---

## 👤 Datos del Estudiante

| Campo | Detalle |
|-------|---------|
| **Nombre** | Joshua Arias |
| **Matrícula** | Al03043935 |
| **Carrera** | Ingeniería en Desarrollo de Software |
| **Semestre** | 8° |

---

## 📋 Descripción del Proyecto

**SmartCampus Services** es una API REST desarrollada con **FastAPI (Python)** que gestiona servicios universitarios como reservación de aulas, eventos académicos, consulta de horarios y notificaciones institucionales.

Este proyecto implementa un pipeline **DevOps completo** con CI/CD automatizado, desde el código fuente hasta el despliegue en Kubernetes.

---

## 🏗️ Arquitectura del Sistema

```
Developer Push
     │
     ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│  GitHub     │───▶│  GitHub     │───▶│  Amazon ECR  │
│  Repository │    │  Actions CI │    │  (Registry)  │
└─────────────┘    └─────────────┘    └──────┬───────┘
                                             │
                        ┌────────────────────▼───────┐
                        │   GitHub Actions CD (Helm) │
                        └────────────────────┬───────┘
                                             │
                        ┌────────────────────▼───────┐
                        │   Amazon EKS (Kubernetes)  │
                        │  ┌────────────────────────┐ │
                        │  │  smartcampus namespace  │ │
                        │  │  ┌──────┐  ┌──────┐    │ │
                        │  │  │ Pod  │  │ Pod  │    │ │
                        │  │  └──────┘  └──────┘    │ │
                        │  └────────────────────────┘ │
                        └────────────────────────────┘
```

---

## ✅ Prerrequisitos

Herramientas necesarias en tu máquina local:

| Herramienta | Versión | Instalación |
|-------------|---------|-------------|
| Terraform | >= 1.5.0 | [terraform.io](https://www.terraform.io) |
| AWS CLI | >= 2.x | [aws.amazon.com/cli](https://aws.amazon.com/cli) |
| kubectl | >= 1.29 | [kubernetes.io/docs](https://kubernetes.io/docs/tasks/tools) |
| Helm | >= 3.14 | [helm.sh](https://helm.sh) |
| Docker | >= 24.x | [docker.com](https://www.docker.com) |
| Git | >= 2.x | [git-scm.com](https://git-scm.com) |

### Configurar AWS CLI

```bash
aws configure
# AWS Access Key ID: [tu-access-key]
# AWS Secret Access Key: [tu-secret-key]
# Default region: us-east-1
# Default output format: json
```

---

## 1️⃣ Infraestructura como Código (Terraform)

### Estructura de archivos Terraform

```
terraform/
├── provider.tf    # Configuración del proveedor AWS y backend S3
├── variables.tf   # Variables parametrizables del proyecto
└── main.tf        # Recursos: VPC, EKS y ECR
```

### Pasos para ejecutar Terraform

```bash
# 1. Entrar al directorio de Terraform
cd terraform/

# 2. Inicializar Terraform (descarga providers y configura backend)
terraform init

# 3. Previsualizar los cambios que se aplicarán (¡siempre hacer esto!)
terraform plan -var="environment=dev"

# 4. Aplicar la infraestructura en AWS (~15-20 minutos para EKS)
terraform apply -var="environment=dev" -auto-approve

# 5. Ver los outputs generados (endpoint del clúster, URL de ECR, etc.)
terraform output
```

### Recursos que crea Terraform

- ✅ **VPC** con subredes públicas y privadas en 2 zonas de disponibilidad
- ✅ **Amazon EKS** clúster Kubernetes v1.29 con auto-scaling (1-4 nodos)
- ✅ **Amazon ECR** repositorio privado con escaneo de vulnerabilidades
- ✅ **NAT Gateway** para que los nodos privados accedan a internet

### Destruir la infraestructura (evitar costos)

```bash
terraform destroy -var="environment=dev" -auto-approve
```

---

## 2️⃣ Pipeline CI — Build y Push de Imagen Docker

### Cómo funciona

El pipeline `ci.yml` se activa **automáticamente con cada `git push`** a las ramas `main`, `develop` o `feature/*`.

```
git push → Tests → Lint → Docker Build → Trivy Scan → Push a ECR
```

### Configurar secretos en GitHub

En tu repositorio GitHub: **Settings → Secrets and variables → Actions**

| Secret | Valor |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Tu Access Key de AWS |
| `AWS_SECRET_ACCESS_KEY` | Tu Secret Key de AWS |

### Ejecución local del Dockerfile

```bash
# Construir la imagen localmente
cd app/
docker build -t smartcampus-app:local .

# Ejecutar el contenedor
docker run -d -p 8000:8000 --name smartcampus smartcampus-app:local

# Probar los endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/servicios

# Detener el contenedor
docker stop smartcampus && docker rm smartcampus
```

---

## 3️⃣ Pipeline CD — Despliegue con Helm en Kubernetes

### Cómo funciona

El pipeline `cd.yml` se activa cuando hay un **merge a la rama `main`**.

```
Merge a main → Validar Helm → Deploy con helm upgrade --install → Verificar pods
```

### Despliegue manual con Helm (desde tu máquina local)

```bash
# 1. Configurar kubectl para conectarse al clúster EKS
aws eks --region us-east-1 update-kubeconfig --name smartcampus-cluster

# 2. Crear el namespace
kubectl create namespace smartcampus

# 3. Instalar o actualizar la aplicación con Helm
helm upgrade --install smartcampus ./helm/smartcampus \
  --namespace smartcampus \
  --set image.repository=<TU_CUENTA>.dkr.ecr.us-east-1.amazonaws.com/smartcampus-services \
  --set image.tag=latest \
  --wait

# 4. Verificar el despliegue
helm status smartcampus -n smartcampus
```

---

## 4️⃣ Verificar que la App está Corriendo en K8s

```bash
# Ver todos los recursos en el namespace smartcampus
kubectl get all -n smartcampus

# Ver el estado de los pods (deben estar en Running)
kubectl get pods -n smartcampus

# Ver los servicios y obtener la IP externa (LoadBalancer)
kubectl get svc -n smartcampus

# Ver logs de un pod en tiempo real
kubectl logs -f deployment/smartcampus-app -n smartcampus

# Ver el HPA (auto-scaling) en acción
kubectl get hpa -n smartcampus

# Describir un pod para diagnosticar problemas
kubectl describe pod -l app=smartcampus -n smartcampus

# Port-forward para acceder desde local sin Load Balancer
kubectl port-forward svc/smartcampus-svc 8080:80 -n smartcampus
# Luego acceder en: http://localhost:8080
```

---

## 📂 Estructura del Repositorio

```
smartcampus-devops/
├── .github/
│   └── workflows/
│       ├── ci.yml          # Pipeline CI: Build & Push
│       └── cd.yml          # Pipeline CD: Deploy con Helm
├── app/
│   ├── main.py             # Aplicación FastAPI
│   ├── requirements.txt    # Dependencias Python
│   └── Dockerfile          # Imagen Docker optimizada
├── helm/
│   └── smartcampus/        # Helm Chart personalizado
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── configmap.yaml
│           └── hpa.yaml
├── terraform/
│   ├── provider.tf         # Proveedor AWS + backend S3
│   ├── variables.tf        # Variables parametrizables
│   └── main.tf             # VPC + EKS + ECR
└── README.md               # Este archivo
```

---

## 🔄 Flujo Git (Estrategia Git Flow)

```
main ──────────────────────────────────────── (producción estable)
  └── develop ───────────────────────────── (desarrollo)
        └── feature/reservacion-aulas ── (nueva funcionalidad)
        └── feature/notificaciones ───── (nueva funcionalidad)
        └── hotfix/fix-health-endpoint ─ (corrección urgente)
```

---

## 🛡️ Seguridad Implementada

- ✅ **Multi-stage Docker build**: imagen final sin herramientas de compilación
- ✅ **Usuario no-root** en el contenedor (principio de mínimo privilegio)
- ✅ **Trivy**: escaneo automático de vulnerabilidades CVE en cada build
- ✅ **ECR scan on push**: AWS escanea imágenes al subirse al registro
- ✅ **Resource limits** en K8s: evita ataques de resource exhaustion
- ✅ **Secretos en GitHub Actions Secrets**: nunca en el código fuente

---

## 📊 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Mensaje de bienvenida |
| GET | `/health` | Health check para Kubernetes |
| GET | `/servicios` | Lista de servicios universitarios |
| GET | `/info` | Información del sistema |
| GET | `/docs` | Documentación Swagger UI (automática) |

---

*Proyecto Integrador DevOps — Ingeniería en Desarrollo de Software — Semestre 8°*
