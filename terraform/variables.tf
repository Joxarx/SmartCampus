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

# Entorno de despliegue (afecta tamaños, réplicas, etc.)
variable "environment" {
  description = "Entorno de despliegue: dev, staging o prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "El entorno debe ser: dev, staging o prod."
  }
}

# Nombre del clúster EKS (Elastic Kubernetes Service)
variable "cluster_name" {
  description = "Nombre del clúster de Kubernetes (EKS)"
  type        = string
  default     = "smartcampus-cluster"
}

# Versión de Kubernetes a usar en EKS
variable "kubernetes_version" {
  description = "Versión de Kubernetes para el clúster EKS"
  type        = string
  default     = "1.29"
}

# Tipo de instancia EC2 para los nodos workers del clúster
variable "node_instance_type" {
  description = "Tipo de instancia EC2 para los nodos de trabajo"
  type        = string
  default     = "t3.medium" # 2 vCPU, 4 GB RAM - adecuado para dev
}

# Número de nodos en el grupo de workers
variable "node_desired_count" {
  description = "Número deseado de nodos workers en el clúster"
  type        = number
  default     = 2
}

variable "node_min_count" {
  description = "Número mínimo de nodos (auto-scaling)"
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Número máximo de nodos (auto-scaling)"
  type        = number
  default     = 4
}

# Bloques CIDR para la VPC (red privada virtual)
variable "vpc_cidr" {
  description = "Bloque CIDR para la VPC del proyecto"
  type        = string
  default     = "10.0.0.0/16"
}

# Subredes privadas donde vivirán los nodos de Kubernetes
variable "private_subnets" {
  description = "CIDRs para subredes privadas (nodos EKS)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

# Subredes públicas para los Load Balancers expuestos a internet
variable "public_subnets" {
  description = "CIDRs para subredes públicas (Load Balancers)"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

# Nombre del repositorio en ECR (Elastic Container Registry)
variable "ecr_repo_name" {
  description = "Nombre del repositorio en Amazon ECR"
  type        = string
  default     = "smartcampus-services"
}
