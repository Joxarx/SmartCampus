# 🎓 SmartCampus Services — Proyecto Integrador DevOps

<p align="center">
  <img src="https://img.shields.io/badge/DevOps-Pipeline-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Python-3.11-yellow?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/AWS-EC2_Free_Tier-FF9900?style=for-the-badge&logo=amazon-aws" />
  <img src="https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform" />
  <img src="https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker" />
  <img src="https://img.shields.io/badge/Vault-Secrets-000000?style=for-the-badge&logo=vault" />
  <img src="https://img.shields.io/badge/Ansible-Provisioning-EE0000?style=for-the-badge&logo=ansible" />
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

Este proyecto implementa un pipeline **DevOps completo** con CI/CD automatizado, desde el código fuente hasta el despliegue en una instancia EC2 Free Tier de AWS, con gestión centralizada de secretos mediante **HashiCorp Vault**.

---

## 🏗️ Arquitectura del Sistema

```
Developer Push
     │
     ▼
┌─────────────┐    ┌──────────────────────────────────────┐
│  GitHub     │    │          GitHub Actions               │
│  Repository │───▶│                                      │
└─────────────┘    │  1. Lee VAULT_TOKEN (GitHub Secret)  │
                   │  2. Consulta Vault EC2 :8200          │
                   │  3. Obtiene AWS_ACCESS_KEY_ID         │
                   │     y AWS_SECRET_ACCESS_KEY           │
                   └─────────┬──────────────┬─────────────┘
                             │              │
                   ┌─────────▼──────┐  ┌───▼──────────────┐
                   │ HashiCorp Vault │  │   Amazon ECR      │
                   │ EC2 :8200       │  │   (Registry)      │
                   │ (Secrets Store) │  └───────┬───────────┘
                   └─────────────────┘          │
                                       ┌────────▼──────────┐
                                       │  GitHub Actions CD │
                                       │  (SSM send-command)│
                                       └────────┬───────────┘
                                                │
                                    ┌───────────▼──────────┐
                                    │  Amazon EC2 (App)     │
                                    │  t2.micro / t3.micro  │
                                    │  ┌──────────────────┐ │
                                    │  │ Docker Container  │ │
                                    │  │ FastAPI :8000     │ │
                                    │  └──────────────────┘ │
                                    └──────────────────────┘
```

**Dos instancias EC2 en la misma VPC:**

| Instancia | Acceso | Puerto | Función |
|-----------|--------|--------|---------|
| **App EC2** | SSM only | 8000 | Ejecuta el contenedor FastAPI |
| **Vault EC2** | SSH (Ansible) + API | 22, 8200 | Almacén central de secretos |

---

## ✅ Prerrequisitos

Herramientas necesarias en tu máquina local:

| Herramienta | Versión | Instalación |
|-------------|---------|-------------|
| Terraform | >= 1.5.0 | [terraform.io](https://www.terraform.io) |
| AWS CLI | >= 2.x | [aws.amazon.com/cli](https://aws.amazon.com/cli) |
| Ansible | >= 2.15 | `pip install ansible` |
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
├── main.tf        # Recursos App: VPC, EC2 y ECR
└── vault.tf       # Recursos Vault: EC2, Security Group, IAM Role
```

### Paso previo: crear el bucket S3 para el estado remoto

El bucket debe existir **antes** de ejecutar `terraform init`:

```bash
aws s3 mb s3://smartcampus-terraform-state --region us-east-1
```

### Paso previo: crear un Key Pair para la instancia Vault

Ansible accede a Vault via SSH. Crea un Key Pair en AWS y descarga el `.pem`:

```bash
aws ec2 create-key-pair \
  --key-name vault-key \
  --query 'KeyMaterial' \
  --output text > ~/.ssh/vault-key.pem

chmod 400 ~/.ssh/vault-key.pem
```

### Pasos para ejecutar Terraform

```bash
# 1. Entrar al directorio de Terraform
cd terraform/

# 2. Inicializar Terraform (descarga providers y configura backend S3)
terraform init

# 3. Previsualizar los cambios que se aplicarán
terraform plan \
  -var="environment=dev" \
  -var="vault_key_name=vault-key" \
  -var="vault_admin_cidr=$(curl -s ifconfig.me)/32"

# 4. Aplicar la infraestructura en AWS (~3-5 minutos)
terraform apply \
  -var="environment=dev" \
  -var="vault_key_name=vault-key" \
  -var="vault_admin_cidr=$(curl -s ifconfig.me)/32"

# 5. Ver los outputs generados
terraform output
```

### Variables de Terraform

| Variable | Descripción | Default |
|----------|-------------|---------|
| `environment` | Entorno: `dev`, `staging`, `prod` | `dev` |
| `aws_region` | Región AWS | `us-east-1` |
| `instance_type` | Tipo EC2 (vacío = auto Free Tier) | `""` |
| `vault_key_name` | Key Pair SSH para la instancia Vault | *requerido* |
| `vault_admin_cidr` | CIDR permitido en puerto 22 de Vault | `0.0.0.0/0` |

### Recursos que crea Terraform

**App EC2 (`main.tf`):**
- ✅ **VPC** con una subred pública en `us-east-1a`
- ✅ **Security Group** con puerto 8000 abierto (FastAPI)
- ✅ **IAM Role + Instance Profile** con permisos ECR y SSM
- ✅ **Amazon EC2** t2.micro/t3.micro con Docker vía `user_data`
- ✅ **Amazon ECR** repositorio privado con escaneo automático

**Vault EC2 (`vault.tf`):**
- ✅ **Security Group** con puerto 22 (SSH restringido) y 8200 (API Vault)
- ✅ **IAM Role + Instance Profile** con permisos SSM
- ✅ **Amazon EC2** t2.micro/t3.micro — Ansible instala Vault

### Destruir la infraestructura (evitar costos)

```bash
terraform destroy \
  -var="environment=dev" \
  -var="vault_key_name=vault-key"
```

---

## 2️⃣ Provisionar Vault con Ansible

Después de `terraform apply`, Ansible instala y configura HashiCorp Vault en la instancia Vault EC2.

### Estructura de Ansible

```
ansible/
├── site.yml                          # Playbook principal
├── inventory/
│   └── hosts.ini                     # IPs de los servidores Vault
├── group_vars/
│   └── vault.yml                     # Variables del grupo vault_servers
└── roles/vault/
    ├── defaults/main.yml             # vault_version, puertos, paths, TTL
    ├── handlers/main.yml             # reload systemd + restart vault
    ├── templates/
    │   ├── vault.hcl.j2              # Configuración de Vault (storage, listener)
    │   └── vault.service.j2          # Unit de systemd con CAP_IPC_LOCK
    └── tasks/
        ├── main.yml                  # Orquestador: install → configure → init → kv
        ├── install.yml               # Usuario, directorios, binario, setcap
        ├── configure.yml             # Deploy de templates, arranque del servicio
        ├── init_unseal.yml           # vault operator init + unseal (idempotente)
        └── kv_secrets.yml            # KV v2, política cicd-policy, token, secretos
```

### Pasos para provisionar Vault

```bash
# 1. Obtener la IP de la instancia Vault
terraform output vault_public_ip
# → 1.2.3.4

# 2. Copiar la línea lista para el inventario
terraform output vault_ansible_inventory_line
# → vault_server ansible_host=1.2.3.4 ansible_user=ec2-user ansible_ssh_private_key_file=~/.ssh/vault-key.pem

# 3. Pegar esa línea en ansible/inventory/hosts.ini

# 4. Ejecutar el playbook (~3-5 minutos)
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.ini
```

### Lo que hace el playbook

| Fase | Tarea |
|------|-------|
| **install** | Crea usuario `vault`, descarga binario v1.17.2, asigna `CAP_IPC_LOCK` |
| **configure** | Despliega `vault.hcl` y unit de systemd, arranca el servicio |
| **init_unseal** | `vault operator init` (1 key share), guarda `.vault-init.json` localmente, unseal |
| **kv_secrets** | Habilita KV v2, crea política `cicd-policy`, genera token CI/CD, escribe secretos placeholder |

### Secretos en Vault

```
secret/smartcampus/aws
  ├── AWS_ACCESS_KEY_ID     → "PLACEHOLDER_REPLACE_IN_VAULT_UI"
  └── AWS_SECRET_ACCESS_KEY → "PLACEHOLDER_REPLACE_IN_VAULT_UI"

secret/smartcampus/app
  ├── ENVIRONMENT           → "production"
  └── APP_VERSION           → "latest"
```

### Política `cicd-policy` (GitHub Actions — solo lectura)

```hcl
path "secret/data/smartcampus/*"     { capabilities = ["read", "list"] }
path "secret/metadata/smartcampus/*" { capabilities = ["list"] }
```

### Al finalizar el playbook

El output imprime los valores que debes guardar:

```
► VAULT_ADDR  = http://<VAULT_IP>:8200
► VAULT_TOKEN = hvs.xxxxxxxxxxxxxxxxxx
```

> **Guarda `.vault-init.json`** en un lugar seguro — contiene el unseal key y el root token.
> Este archivo está en `.gitignore` y **nunca debe commitearse**.

---

## 3️⃣ Configurar Secretos en GitHub

Después del playbook, configura estos dos secretos en tu repositorio:
**Settings → Secrets and variables → Actions**

| Secret | Valor |
|--------|-------|
| `VAULT_ADDR` | `http://<vault_public_ip>:8200` |
| `VAULT_TOKEN` | Token CI/CD impreso por Ansible |

Luego actualiza las credenciales reales de AWS en la UI de Vault:

```
http://<VAULT_IP>:8200/ui
Login: root token de .vault-init.json
Ruta: secret/smartcampus/aws
```

Una vez actualizado, **elimina** `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` de GitHub Secrets.

---

## 4️⃣ Pipeline CI — Build y Push de Imagen Docker

### Cómo funciona

El pipeline `ci.yml` se activa **automáticamente con cada `git push`** a las ramas `main`, `develop` o `feature/*` cuando hay cambios en `app/`.

```
git push
  → Tests (pytest + flake8)
  → Lee AWS creds desde Vault
  → Docker Build
  → Trivy Scan
  → Push a ECR
```

### Ejecución local del Dockerfile

```bash
# Construir la imagen localmente
docker build -t smartcampus-app:local ./app

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

## 5️⃣ Pipeline CD — Despliegue via SSM en EC2

### Cómo funciona

El pipeline `cd.yml` se activa cuando hay un **merge a la rama `main`** y requiere aprobación manual del entorno `production` en GitHub.

```
Merge a main
  → Aprobación manual
  → Lee AWS creds desde Vault
  → SSM send-command
  → docker pull + run
  → Verificar /health
```

### Configurar el entorno de producción en GitHub

En **Settings → Environments → New environment** crea uno llamado `production` y activa **Required reviewers**.

### Verificar el despliegue manualmente

```bash
# Obtener la IP pública y URL de la app
terraform output app_url
# → http://<PUBLIC_IP>:8000

# Conectarse a la instancia via SSM (sin SSH, sin puerto 22)
terraform output ssm_connect
# → aws ssm start-session --target i-xxxx --region us-east-1

# Ver el contenedor corriendo en la instancia
aws ssm send-command \
  --instance-ids <INSTANCE_ID> \
  --document-name "AWS-RunShellScript" \
  --parameters commands='["docker ps --format \"table {{.Names}}\\t{{.Status}}\\t{{.Image}}\""]' \
  --query 'Command.CommandId' --output text
```

---

## 6️⃣ Verificar que la App está Corriendo

```bash
# Obtener la URL pública desde Terraform
terraform output app_url

# Probar el endpoint de salud
curl http://<PUBLIC_IP>:8000/health
# → {"status": "healthy", ...}

# Probar los demás endpoints
curl http://<PUBLIC_IP>:8000/
curl http://<PUBLIC_IP>:8000/servicios
curl http://<PUBLIC_IP>:8000/info

# Ver logs del contenedor (via SSM)
aws ssm start-session --target <INSTANCE_ID> --region us-east-1
# Dentro de la sesión SSM:
# docker logs smartcampus --tail 50 -f
```

---

## 📂 Estructura del Repositorio

```
SmartCampus/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Pipeline CI: Test → Vault → Build → Push a ECR
│       └── cd.yml              # Pipeline CD: Vault → Deploy via SSM a EC2
├── ansible/
│   ├── site.yml                # Playbook principal: provisiona HashiCorp Vault
│   ├── inventory/
│   │   └── hosts.ini           # IP de la instancia Vault (completar tras TF apply)
│   ├── group_vars/
│   │   └── vault.yml           # Variables de grupo para vault_servers
│   └── roles/vault/
│       ├── defaults/main.yml   # Versión, puertos, paths, TTL del token
│       ├── handlers/main.yml   # Handlers: reload systemd, restart vault
│       ├── templates/
│       │   ├── vault.hcl.j2    # Configuración de Vault
│       │   └── vault.service.j2 # Unit systemd con CAP_IPC_LOCK
│       └── tasks/
│           ├── main.yml        # Orquestador de tareas
│           ├── install.yml     # Binario, usuario, directorios, setcap
│           ├── configure.yml   # Templates + servicio systemd
│           ├── init_unseal.yml # Init (idempotente), guarda .vault-init.json
│           └── kv_secrets.yml  # KV v2, política, token CI/CD, secretos
├── app/
│   ├── main.py                 # Aplicación FastAPI
│   ├── requirements.txt        # Dependencias Python
│   ├── tests/                  # Pruebas unitarias (pytest)
│   └── Dockerfile              # Imagen Docker multi-stage optimizada
├── helm/smartcampus/           # Helm chart (referencia, no usado en producción)
├── terraform/
│   ├── provider.tf             # Proveedor AWS + backend S3
│   ├── variables.tf            # Variables parametrizables
│   ├── main.tf                 # VPC + App EC2 + ECR
│   └── vault.tf                # Vault EC2 + Security Group + IAM
└── README.md                   # Este archivo
```

---

## 🔄 Flujo End-to-End Completo

```bash
# ── Infraestructura ───────────────────────────────────────────
terraform apply -var="environment=dev" -var="vault_key_name=vault-key"

# ── Vault ─────────────────────────────────────────────────────
# 1. Edita ansible/inventory/hosts.ini con la IP de Vault
ansible-playbook ansible/site.yml -i ansible/inventory/hosts.ini
# → Imprime VAULT_ADDR y VAULT_TOKEN

# 2. Añade VAULT_ADDR y VAULT_TOKEN a GitHub Secrets
# 3. Actualiza credenciales reales en Vault UI: secret/smartcampus/aws
# 4. Elimina AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY de GitHub Secrets

# ── Desarrollo continuo ───────────────────────────────────────
git push origin feature/nueva-funcionalidad
# → CI lee credenciales de Vault → build → push a ECR

git checkout main && git merge feature/nueva-funcionalidad && git push
# → CD lee credenciales de Vault → despliega en EC2 via SSM
```

---

## 🔄 Flujo Git

```
main ──────────────────────────────────────── (producción estable)
  └── develop ───────────────────────────── (desarrollo)
        └── feature/reservacion-aulas ── (nueva funcionalidad)
        └── feature/notificaciones ───── (nueva funcionalidad)
        └── hotfix/fix-health-endpoint ─ (corrección urgente)
```

---

## 🛡️ Seguridad Implementada

- ✅ **HashiCorp Vault**: secretos AWS externalizados — nunca en GitHub como variables en texto plano
- ✅ **Política de mínimo privilegio en Vault**: el token CI/CD solo puede leer `secret/smartcampus/*`
- ✅ **Token de larga duración renovable**: TTL de 10 años, sin necesidad de rotar manualmente
- ✅ **SSH restringido**: puerto 22 de Vault limitado a `vault_admin_cidr` (tu IP)
- ✅ **CAP_IPC_LOCK en Vault**: la memoria del proceso Vault no puede ser volcada a disco
- ✅ **`.vault-init.json` en `.gitignore`**: unseal key y root token nunca se commitean
- ✅ **Multi-stage Docker build**: imagen final sin herramientas de compilación
- ✅ **Usuario no-root** en el contenedor (principio de mínimo privilegio)
- ✅ **Trivy**: escaneo automático de vulnerabilidades CVE en cada build
- ✅ **ECR scan on push**: AWS escanea imágenes al subirse al registro
- ✅ **SSM Session Manager**: acceso remoto a App EC2 sin abrir puerto 22

---

## 📊 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Mensaje de bienvenida |
| GET | `/health` | Health check del contenedor |
| GET | `/servicios` | Lista de servicios universitarios |
| GET | `/info` | Información del sistema |
| GET | `/docs` | Documentación Swagger UI (automática) |

---

*Proyecto Integrador DevOps — Ingeniería en Desarrollo de Software — Semestre 8°*
