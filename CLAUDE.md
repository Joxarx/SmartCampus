# SmartCampus Services

University campus management platform (classroom reservations, events, schedules, notifications).
Full GitOps pipeline: FastAPI app → Docker image → ECR → EC2 via SSM.

## Tech Stack

| Layer         | Technology                                        |
|---------------|---------------------------------------------------|
| IaC           | Terraform >= 1.5, AWS provider ~> 5.0             |
| Cloud         | AWS: EC2 (Free Tier), ECR, VPC, S3 (state)       |
| App           | Python 3.11, FastAPI 0.111.0, Uvicorn             |
| Container     | Docker (multi-stage builds)                       |
| Deploy        | AWS SSM Session Manager (no SSH, no kubectl)      |
| CI/CD         | GitHub Actions                                    |

## Project Structure

```
SmartCampus/
├── terraform/           # All AWS infrastructure
│   ├── provider.tf      # AWS provider config + S3 remote state backend (use_lockfile)
│   ├── variables.tf     # All parameterizable inputs (region, env, instance type, CIDRs)
│   └── main.tf          # Module composition: VPC → EC2 → ECR + outputs
├── app/
│   ├── main.py          # All API endpoints: /, /health, /servicios, /info
│   └── Dockerfile       # Multi-stage build (builder + runtime stages)
├── helm/smartcampus/    # Kept for reference — NOT used in active deployment
└── .github/workflows/
    ├── ci.yml           # Triggers on app/** changes: test → build → Trivy scan → ECR push
    └── cd.yml           # Triggers on main: SSM → EC2 docker pull + run (requires approval)
```

## Essential Commands

### Terraform

```bash
terraform init                              # Download modules, configure S3 backend
terraform plan  -var="environment=dev"      # Preview changes
terraform apply -var="environment=dev"      # Provision/update infrastructure
terraform output                            # Print EC2 public IP, app URL, SSM connect cmd
terraform destroy -var="environment=dev"    # Tear down all resources
```

Valid `environment` values: `dev`, `staging`, `prod` — see `terraform/variables.tf:19-23`.

### Application (local)

```bash
docker build -t smartcampus-app:local ./app
docker run -p 8000:8000 smartcampus-app:local
# Swagger UI auto-generated at http://localhost:8000/docs
```

### EC2 / SSM

```bash
# Get the public IP and app URL
terraform output app_url                    # → http://<PUBLIC_IP>:8000

# Connect to the instance interactively via SSM (no SSH or port 22 needed)
terraform output ssm_connect               # prints the command below
aws ssm start-session --target <INSTANCE_ID> --region us-east-1

# Check running container on the instance
aws ssm send-command \
  --instance-ids <INSTANCE_ID> \
  --document-name "AWS-RunShellScript" \
  --parameters commands='["docker ps"]' \
  --query 'Command.CommandId' --output text
```

## Required Secrets (GitHub Actions)

`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — used in `.github/workflows/ci.yml:87-89`
and `.github/workflows/cd.yml:43-45`. The CD pipeline also requires a `production` environment
configured in GitHub with manual approval rules.

## Key File References

- Remote state backend config: `terraform/provider.tf:23-30`
- Global AWS resource tags: `terraform/provider.tf:37-44`
- EC2 instance definition + user_data bootstrap: `terraform/main.tf:124-170`
- ECR lifecycle policy (keeps 10 images): `terraform/main.tf:192-207`
- Health check endpoint (used by Docker HEALTHCHECK): `app/main.py:34-49`
- Non-root container user setup: `app/Dockerfile:48-49`
- CD deploy via SSM send-command: `.github/workflows/cd.yml:89-116`

## Additional Documentation

| Topic                                    | File                                     |
|------------------------------------------|------------------------------------------|
| Architectural patterns & design decisions | `.claude/docs/architectural_patterns.md` |
