# ============================================================
# variables.tf - Declaración de variables parametrizables
# Permite reutilizar el código en múltiples entornos
# ============================================================

# Región de AWS donde se desplegará toda la infraestructura
variable "aws_region" {
  description = "Región de AWS para el despliegue"
  type        = string
  default     = "us-east-1"
}

# Entorno de despliegue (afecta configuración de la app)
variable "environment" {
  description = "Entorno de despliegue: dev, staging o prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "El entorno debe ser: dev, staging o prod."
  }
}

# Nombre base del proyecto (usado en nombres de recursos de AWS)
variable "cluster_name" {
  description = "Nombre base del proyecto (prefijo de recursos AWS)"
  type        = string
  default     = "smartcampus"
}

# Tipo de instancia EC2.
# Dejar vacío ("") para auto-detectar cuál es Free Tier en esta cuenta/región
# (puede ser t2.micro o t3.micro según la cuenta y la región).
variable "instance_type" {
  description = "Tipo de instancia EC2 (vacío = auto-detectar Free Tier eligible)"
  type        = string
  default     = "" # Auto-detect: t2.micro o t3.micro según la cuenta/región
}

# Nombre del par de claves SSH (opcional).
# Dejar vacío ("") para usar solo SSM Session Manager (más seguro, sin abrir puerto 22).
variable "key_name" {
  description = "Nombre del par de claves SSH en AWS (vacío = solo SSM)"
  type        = string
  default     = ""
}

# Bloques CIDR para la VPC (red privada virtual)
variable "vpc_cidr" {
  description = "Bloque CIDR para la VPC del proyecto"
  type        = string
  default     = "10.0.0.0/16"
}

# Subred pública donde vivirá la instancia EC2.
# Una sola AZ es suficiente para Free Tier (sin NAT Gateway).
variable "public_subnets" {
  description = "CIDRs para subredes públicas (instancia EC2)"
  type        = list(string)
  default     = ["10.0.101.0/24"]
}

# Nombre del repositorio en ECR (Elastic Container Registry)
variable "ecr_repo_name" {
  description = "Nombre del repositorio en Amazon ECR"
  type        = string
  default     = "smartcampus-services"
}

# ── VAULT: Variables para la instancia HashiCorp Vault ───────

# Nombre del par de claves SSH para la instancia Vault.
# Requerido: Ansible necesita SSH para provisionar Vault.
variable "vault_key_name" {
  description = "Nombre del par de claves SSH en AWS para la instancia Vault (requerido para Ansible)"
  type        = string
}

# CIDR que puede conectarse por SSH al servidor Vault.
# Restringe a tu IP: e.g. terraform apply -var="vault_admin_cidr=203.0.113.0/32"
variable "vault_admin_cidr" {
  description = "CIDR permitido para SSH (puerto 22) en la instancia Vault. Restringe a tu IP para mayor seguridad."
  type        = string
  default     = "0.0.0.0/0"
}
