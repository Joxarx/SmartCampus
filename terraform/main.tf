# ============================================================
# main.tf - Recursos principales de infraestructura
# Provisiona: VPC (pública), IAM, ECR y EC2 Free Tier (t2.micro o t3.micro)
# ============================================================

# ── MÓDULO: VPC ─────────────────────────────────────────────
# Red virtual privada simplificada: una sola subred pública,
# sin NAT Gateway (ahorra ~$32/mes y no es necesario para EC2 público).
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.cluster_name}-vpc"
  cidr = var.vpc_cidr

  # Una sola zona de disponibilidad es suficiente para Free Tier
  azs            = ["${var.aws_region}a"]
  public_subnets = var.public_subnets

  # Sin NAT Gateway: los nodos son públicos y no lo necesitan
  enable_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# ── SECURITY GROUP: Acceso HTTP a la aplicación ───────────────
# Permite tráfico entrante en el puerto 8000 (FastAPI)
# y salida a internet (para descargar imágenes de ECR).
resource "aws_security_group" "app" {
  name        = "${var.cluster_name}-app-sg"
  description = "Permite acceso HTTP a la app SmartCampus"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "FastAPI HTTP"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Salida a internet (ECR, actualizaciones)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── IAM: Rol para que EC2 pueda leer de ECR y usar SSM ────────
# Sin este rol, la instancia no podría hacer docker pull desde ECR.
resource "aws_iam_role" "ec2_ecr_role" {
  name = "${var.cluster_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Permiso para leer imágenes de ECR (docker pull)
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Permiso para SSM Session Manager (acceso remoto sin abrir puerto 22)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# El instance profile es el "puente" entre el rol IAM y la instancia EC2
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.cluster_name}-ec2-profile"
  role = aws_iam_role.ec2_ecr_role.name
}

# ── INSTANCIA FREE TIER: auto-detección del tipo correcto ────
# Distintas cuentas/regiones ofrecen t2.micro o t3.micro como Free Tier.
# Este data source consulta la API de AWS para encontrar cuál aplica aquí.
data "aws_ec2_instance_types" "free_tier" {
  filter {
    name   = "free-tier-eligible"
    values = ["true"]
  }
  # Filtramos solo las variantes micro de la familia t2/t3
  filter {
    name   = "instance-type"
    values = ["t2.micro", "t3.micro"]
  }
}

locals {
  # Si el usuario especificó un tipo, usarlo; si no, tomar el primero
  # que AWS confirme como Free Tier en esta cuenta/región.
  instance_type = var.instance_type != "" ? var.instance_type : tolist(data.aws_ec2_instance_types.free_tier.instance_types)[0]
}

# ── AMI: Amazon Linux 2023 (imagen base del sistema operativo) ─
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── EC2: Instancia Free Tier (t2.micro o t3.micro según cuenta) ─
# Ejecuta directamente el contenedor Docker con la aplicación FastAPI.
# Reemplaza el clúster EKS completo (~$170/mes → $0 en Free Tier).
resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = local.instance_type
  subnet_id              = module.vpc.public_subnets[0]
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  # IP pública fija: necesaria para acceder a la app desde internet
  associate_public_ip_address = true

  # Clave SSH opcional (dejar vacío = usar solo SSM para acceso)
  key_name = var.key_name != "" ? var.key_name : null

  # user_data: script que se ejecuta UNA VEZ al lanzar la instancia
  # Instala Docker, se autentica en ECR y arranca el contenedor
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Actualizar sistema e instalar Docker y AWS CLI
    dnf update -y
    dnf install -y docker aws-cli
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user

    # Autenticarse en ECR y descargar la imagen más reciente
    # (|| true evita fallos si aún no se ha subido ninguna imagen)
    aws ecr get-login-password --region ${var.aws_region} | \
      docker login --username AWS --password-stdin ${aws_ecr_repository.smartcampus.repository_url} || true

    docker pull ${aws_ecr_repository.smartcampus.repository_url}:latest || true

    # Iniciar el contenedor con reinicio automático ante fallos
    docker run -d \
      --name smartcampus \
      --restart unless-stopped \
      -p 8000:8000 \
      -e ENVIRONMENT=production \
      -e APP_VERSION=latest \
      ${aws_ecr_repository.smartcampus.repository_url}:latest || true
  EOF

  tags = {
    Name = "${var.cluster_name}-app"
  }
}

# ── RECURSO: ECR (Container Registry) ───────────────────────
# Registro privado de imágenes Docker en AWS.
# El pipeline CI construye y sube la imagen aquí.
resource "aws_ecr_repository" "smartcampus" {
  name                 = var.ecr_repo_name
  image_tag_mutability = "MUTABLE" # Permite sobreescribir el tag :latest
  force_delete         = true      # Permite borrar el repo aunque tenga imágenes

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
# Mantiene solo las últimas 10 para no superar el límite Free Tier (500 MB).
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
output "app_public_ip" {
  description = "IP pública de la instancia EC2"
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "URL de la aplicación SmartCampus"
  value       = "http://${aws_instance.app.public_ip}:8000"
}

output "ecr_repository_url" {
  description = "URL del repositorio ECR para hacer push de imágenes"
  value       = aws_ecr_repository.smartcampus.repository_url
}

output "ssm_connect" {
  description = "Comando para conectarse a la instancia via AWS SSM (sin SSH)"
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.aws_region}"
}
