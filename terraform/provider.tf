# ============================================================
# provider.tf - Configuración del proveedor de nube (AWS)
# SmartCampus Services - Proyecto Integrador DevOps
# Autor: Joshua Arias | Matrícula: Al03043935
# ============================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Backend S3: el estado de Terraform se guarda remotamente.
  # Esto permite colaboración entre equipos y evita conflictos.
  backend "s3" {
    bucket         = "smartcampus-terraform-state"
    key            = "eks/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "smartcampus-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  # Tags globales: se aplican a TODOS los recursos de AWS creados.
  # Facilita auditoría, gestión de costos y seguridad.
  default_tags {
    tags = {
      Project     = "SmartCampus"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Joshua-Arias"
    }
  }
}
