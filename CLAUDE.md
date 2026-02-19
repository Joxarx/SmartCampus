# SmartCampus Services

University campus management platform (classroom reservations, events, schedules, notifications).
Full GitOps pipeline: FastAPI app → Docker image → ECR → EKS via Helm.

## Tech Stack

| Layer         | Technology                                      |
|---------------|-------------------------------------------------|
| IaC           | Terraform >= 1.5, AWS provider ~> 5.0           |
| Cloud         | AWS: EKS, ECR, VPC, S3 (state), DynamoDB (locks)|
| App           | Python 3.11, FastAPI 0.111.0, Uvicorn           |
| Container     | Docker (multi-stage builds)                     |
| Orchestration | Kubernetes 1.29 on EKS, Helm v3.14              |
| CI/CD         | GitHub Actions                                  |

## Project Structure

```
SmartCampus/
├── terraform/           # All AWS infrastructure
│   ├── provider.tf      # AWS provider config + S3/DynamoDB remote state backend
│   ├── variables.tf     # All parameterizable inputs (region, env, node counts, CIDRs)
│   └── main.tf          # Module composition: VPC → EKS → ECR + outputs
├── app/
│   ├── main.py          # All API endpoints: /, /health, /servicios, /info
│   └── Dockerfile       # Multi-stage build (builder + runtime stages)
├── helm/smartcampus/
│   ├── values.yaml      # All tunable defaults: replicas, resources, probes, HPA
│   └── templates/       # Deployment, Service, HPA, ConfigMap manifests
└── .github/workflows/
    ├── ci.yml           # Triggers on app/** changes: test → build → Trivy scan → ECR push
    └── cd.yml           # Triggers on main: helm lint → deploy to EKS (requires approval)
```

## Essential Commands

### Terraform

```bash
terraform init                              # Download modules, configure S3 backend
terraform plan  -var="environment=dev"      # Preview changes
terraform apply -var="environment=dev"      # Provision/update infrastructure
terraform output                            # Print cluster endpoint, ECR URL, kubectl cmd
terraform destroy -var="environment=dev"    # Tear down all resources
```

Valid `environment` values: `dev`, `staging`, `prod` — see `terraform/variables.tf:19-23`.

### Application (local)

```bash
docker build -t smartcampus-app:local ./app
docker run -p 8000:8000 smartcampus-app:local
# Swagger UI auto-generated at http://localhost:8000/docs
```

### Kubernetes / Helm

```bash
# Configure kubectl (also printed by `terraform output configure_kubectl`)
aws eks --region us-east-1 update-kubeconfig --name smartcampus-cluster

# Deploy or upgrade
helm upgrade --install smartcampus ./helm/smartcampus \
  --namespace smartcampus \
  --set image.repository=<ECR_URL>/smartcampus-services \
  --set image.tag=<7-char-commit-sha> \
  --atomic --timeout 5m

# Inspect
kubectl get pods,svc,hpa -n smartcampus
helm history smartcampus -n smartcampus

# Validate chart locally
helm lint ./helm/smartcampus
helm template smartcampus ./helm/smartcampus --set image.tag=preview
```

## Required Secrets (GitHub Actions)

`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` — used in `.github/workflows/ci.yml:87-89`
and `.github/workflows/cd.yml:70-72`. The CD pipeline also requires a `production` environment
configured in GitHub with manual approval rules.

## Key File References

- Remote state backend config: `terraform/provider.tf:23-29`
- Global AWS resource tags: `terraform/provider.tf:37-44`
- Node group auto-scaling bounds: `terraform/main.tf:56-58`
- ECR lifecycle policy (keeps 10 images): `terraform/main.tf:94-109`
- Health check endpoint (used by K8s probes): `app/main.py:34-49`
- Non-root container user setup: `app/Dockerfile:48-49`
- Zero-downtime rolling update config: `helm/smartcampus/values.yaml:63-67`
- Topology spread constraints: `helm/smartcampus/templates/deployment.yaml:50-56`

## Additional Documentation

| Topic                                    | File                                     |
|------------------------------------------|------------------------------------------|
| Architectural patterns & design decisions | `.claude/docs/architectural_patterns.md` |
