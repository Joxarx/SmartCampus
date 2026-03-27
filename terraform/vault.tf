# ============================================================
# vault.tf - HashiCorp Vault EC2 + recursos de soporte
# Provisiona: Security Group, IAM Role, EC2 para Vault server
# Ansible (ansible/site.yml) instala y configura Vault sobre esta instancia.
# ============================================================

# ── SECURITY GROUP: Vault server ─────────────────────────────
# Puerto 22: solo desde vault_admin_cidr (para Ansible via SSH)
# Puerto 8200: abierto para que GitHub Actions acceda a la API de Vault
resource "aws_security_group" "vault" {
  name        = "${var.cluster_name}-vault-sg"
  description = "Security group para HashiCorp Vault server"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "SSH para Ansible (restringido a vault_admin_cidr)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vault_admin_cidr]
  }

  ingress {
    description = "Vault API y UI (acceso desde GitHub Actions y navegador)"
    from_port   = 8200
    to_port     = 8200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Salida a internet (actualizaciones, descarga de binarios)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-vault-sg"
  }
}

# ── IAM: Rol mínimo para la instancia Vault ──────────────────
# SSM permite debugging operacional sin abrir puertos adicionales.
resource "aws_iam_role" "vault_ec2_role" {
  name = "${var.cluster_name}-vault-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "vault_ssm" {
  role       = aws_iam_role.vault_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "vault_profile" {
  name = "${var.cluster_name}-vault-ec2-profile"
  role = aws_iam_role.vault_ec2_role.name
}

# ── EC2: Instancia Vault (misma AMI y tipo que la app) ────────
# Usa la misma AMI (Amazon Linux 2023) definida en main.tf.
# Ansible (site.yml) se encarga de instalar y configurar Vault completamente.
resource "aws_instance" "vault" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = local.instance_type
  subnet_id              = module.vpc.public_subnets[0]
  vpc_security_group_ids = [aws_security_group.vault.id]
  iam_instance_profile   = aws_iam_instance_profile.vault_profile.name
  key_name               = var.vault_key_name

  associate_public_ip_address = true

  # Bootstrap mínimo: Ansible hace la instalación completa de Vault
  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y unzip curl libcap
  EOF

  tags = {
    Name    = "${var.cluster_name}-vault"
    Project = "SmartCampus"
    Role    = "vault"
  }
}

# ── OUTPUTS: Info de la instancia Vault ──────────────────────
output "vault_public_ip" {
  description = "IP pública de la instancia Vault — úsala en ansible/inventory/hosts.ini"
  value       = aws_instance.vault.public_ip
}

output "vault_url" {
  description = "URL de la API y UI de HashiCorp Vault"
  value       = "http://${aws_instance.vault.public_ip}:8200"
}

output "vault_instance_id" {
  description = "ID de la instancia EC2 de Vault"
  value       = aws_instance.vault.id
}

output "vault_ssh_command" {
  description = "Comando SSH para conectarse a la instancia Vault"
  value       = "ssh -i ~/.ssh/<tu-key.pem> ec2-user@${aws_instance.vault.public_ip}"
}

output "vault_ansible_inventory_line" {
  description = "Línea lista para pegar en ansible/inventory/hosts.ini"
  value       = "vault_server ansible_host=${aws_instance.vault.public_ip} ansible_user=ec2-user ansible_ssh_private_key_file=~/.ssh/<tu-key.pem>"
}
