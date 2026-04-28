# ============================================================
# github_oidc.tf - Federación OIDC entre GitHub Actions y AWS
# Permite que los workflows asuman un rol IAM via tokens efímeros,
# eliminando la necesidad de almacenar AWS_ACCESS_KEY_ID/SECRET en GitHub.
# ============================================================

# ── OIDC PROVIDER ────────────────────────────────────────────
# AWS confía en los tokens emitidos por token.actions.githubusercontent.com.
# Los thumbprints son ignorados por AWS desde 2023 (verificación vía JWKS),
# pero Terraform exige el campo no vacío.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

# ── IAM ROLE: Asumido por workflows del repo SmartCampus ─────
# La condición `sub` restringe qué workflows pueden asumirlo:
# `repo:<owner>/<repo>:*` permite cualquier rama/PR/tag de ese repo.
resource "aws_iam_role" "github_actions" {
  name = "${var.cluster_name}-github-actions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

# ── POLÍTICA: Permisos mínimos para CI (push imagen) y CD (SSM) ─
resource "aws_iam_role_policy" "github_actions" {
  name = "${var.cluster_name}-github-actions-policy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrAuth"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Sid    = "EcrRepoAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
        ]
        Resource = aws_ecr_repository.smartcampus.arn
      },
      {
        Sid      = "Ec2Discovery"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances"]
        Resource = "*"
      },
      {
        # SendCommand requiere autorización sobre el documento Y la instancia.
        # El documento es el shell script estándar de AWS (sin condición).
        Sid      = "SsmSendCommandDocument"
        Effect   = "Allow"
        Action   = ["ssm:SendCommand"]
        Resource = "arn:aws:ssm:*:*:document/AWS-RunShellScript"
      },
      {
        # La instancia destino debe estar tageada Project=SmartCampus.
        Sid      = "SsmSendCommandInstance"
        Effect   = "Allow"
        Action   = ["ssm:SendCommand"]
        Resource = "arn:aws:ec2:*:*:instance/*"
        Condition = {
          StringEquals = { "ssm:resourceTag/Project" = "SmartCampus" }
        }
      },
      {
        Sid    = "SsmInvocationStatus"
        Effect = "Allow"
        Action = [
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
        ]
        Resource = "*"
      },
    ]
  })
}

# ── OUTPUT: ARN para pegar en .github/workflows/*.yml ────────
output "github_actions_role_arn" {
  description = "Role ARN para OIDC desde GitHub Actions. Ya está hardcodeado en los workflows; este output es para referencia."
  value       = aws_iam_role.github_actions.arn
}
