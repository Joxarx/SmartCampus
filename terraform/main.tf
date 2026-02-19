# ============================================================
# main.tf - Recursos principales de infraestructura
# Provisiona: VPC, EKS (Kubernetes) y ECR (Container Registry)
# ============================================================

# ── MÓDULO: VPC ─────────────────────────────────────────────
# Crea la red virtual privada donde residirá toda la infra.
# Usamos el módulo oficial de la comunidad Terraform para VPC.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  # Distribuimos en 2 zonas de disponibilidad para alta disponibilidad
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  # NAT Gateway: permite que los nodos privados salgan a internet
  enable_nat_gateway   = true
  single_nat_gateway   = true  # Solo 1 NAT para ahorrar costos en dev
  enable_dns_hostnames = true  # Necesario para EKS

  # Tags especiales requeridos por EKS para descubrir las subredes
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}

# ── MÓDULO: EKS (Kubernetes) ─────────────────────────────────
# Provisiona un clúster Kubernetes gestionado en AWS (EKS).
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.kubernetes_version

  # El plano de control de EKS se conecta a nuestra VPC
  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  cluster_endpoint_public_access = true  # Permite kubectl desde internet

  # Grupo de nodos workers: las VMs que ejecutarán los pods
  eks_managed_node_groups = {
    smartcampus_nodes = {
      name           = "smartcampus-workers"
      instance_types = [var.node_instance_type]

      # Auto-scaling: se ajusta según la carga de trabajo
      min_size     = var.node_min_count
      max_size     = var.node_max_count
      desired_size = var.node_desired_count

      # Disco de 20 GB por nodo (suficiente para las imágenes Docker)
      disk_size = 20

      labels = {
        Environment = var.environment
        NodeGroup   = "application"
      }
    }
  }

  # Permisos para que EKS gestione recursos de AWS por nosotros
  enable_cluster_creator_admin_permissions = true
}

# ── RECURSO: ECR (Container Registry) ───────────────────────
# Registro privado de imágenes Docker en AWS.
# Aquí se almacenarán las imágenes construidas en el pipeline CI.
resource "aws_ecr_repository" "smartcampus" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE" # Permite sobreescribir el tag :latest

  # Escaneo automático de vulnerabilidades al hacer push de imagen
  image_scanning_configuration {
    scan_on_push = true
  }

  # Cifrado de las imágenes almacenadas en ECR
  encryption_configuration {
    encryption_type = "AES256"
  }
}

# Política de ciclo de vida: elimina imágenes antiguas automáticamente.
# Evita costos excesivos de almacenamiento en ECR.
resource "aws_ecr_lifecycle_policy" "smartcampus" {
  repository = aws_ecr_repository.smartcampus.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Mantener solo las últimas 10 imágenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# ── OUTPUTS: Valores exportados ──────────────────────────────
# Estos valores se usan en el pipeline de CI/CD para configurar
# kubectl y hacer push de imágenes a ECR.

output "cluster_endpoint" {
  description = "Endpoint del API Server de Kubernetes"
  value       = module.eks.cluster_endpoint
}

output "cluster_name" {
  description = "Nombre del clúster EKS"
  value       = module.eks.cluster_name
}

output "ecr_repository_url" {
  description = "URL del repositorio ECR para hacer push de imágenes"
  value       = aws_ecr_repository.smartcampus.repository_url
}

output "configure_kubectl" {
  description = "Comando para configurar kubectl localmente"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${var.cluster_name}"
}
