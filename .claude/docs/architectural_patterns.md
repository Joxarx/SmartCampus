# Architectural Patterns

Patterns that appear across multiple files and inform how this project is structured.

---

## 1. Terraform Module Composition (VPC → EC2 → ECR)

`terraform/main.tf` composes the official `terraform-aws-modules/vpc/aws` module with raw
`aws_instance` and `aws_ecr_repository` resources in dependency order: VPC is provisioned first,
then EC2 references `module.vpc.public_subnets[0]` and `module.vpc.vpc_id`, then ECR is
independent. The VPC module is pinned with `~> 5.0`.

**Implication:** When adding new AWS resources, prefer official modules over raw `resource` blocks
where one exists. Pin with `~>` (pessimistic constraint) to allow patch updates but not majors.

---

## 2. Environment Parameterization with Validation

All environment-specific values flow through `terraform/variables.tf`. The `environment` variable
enforces an allowlist (`dev | staging | prod`) via a `validation` block at `variables.tf:19-23`.
The same environment value propagates to:
- AWS resource tags via `provider.tf:40`
- EC2 instance tags via `main.tf:167-169`
- Container env var `ENVIRONMENT` at runtime via `app/main.py:21`
- SSM deploy command via `cd.yml:97` (`-e ENVIRONMENT=production`)

**Implication:** Never hard-code `dev`/`prod` strings in resource definitions. Pass through
`var.environment` or the equivalent environment variable.

---

## 3. Remote State with S3 Native Locking

`terraform/provider.tf:23-30` stores state in S3 (`smartcampus-terraform-state`) and uses
`use_lockfile = true` for S3-native lock management (no DynamoDB required). The bucket must
exist before `terraform init` can succeed — it is a prerequisite manual resource (not managed
by this Terraform code itself).

**Implication:** The S3 bucket is bootstrapped outside this codebase. Do not add it to
`main.tf` — circular dependency. Create it once with:
`aws s3 mb s3://smartcampus-terraform-state --region us-east-1`

---

## 4. Global Resource Tagging via Provider Default Tags

`terraform/provider.tf:37-44` applies `Project`, `Environment`, `ManagedBy`, and `Owner` tags
to every AWS resource created by the provider — without any per-resource `tags` blocks needed.
Individual resources only add tags when they need resource-specific ones (e.g., the EC2 instance
adds a `Name` tag at `main.tf:167`).

**Implication:** Do not repeat the global tags in individual resource blocks. Add per-resource
`tags` only for resource-specific metadata.

---

## 5. Multi-Stage Docker Build (builder / runtime)

`app/Dockerfile` uses two stages: `builder` installs dependencies into `/install` with
`pip install --prefix`, then `runtime` copies only that directory (`COPY --from=builder`).
The final image is `python:3.11-slim` with no build toolchain, reducing attack surface and
image size. The `requirements.txt` is copied before `main.py` to exploit Docker layer caching
— dependencies only reinstall when `requirements.txt` changes.

**Implication:** Follow the same layer-ordering pattern if adding build steps: copy dependency
manifests first, install, then copy source.

---

## 6. Health Endpoint as the Single Source of Truth for Probes

`app/main.py:34-49` defines `/health` returning `{"status": "healthy", ...}` with HTTP 200.
This same path is referenced in:
- Docker `HEALTHCHECK` at `app/Dockerfile:56-57`
- CD health verification loop at `.github/workflows/cd.yml:133`

**Implication:** If the health endpoint path changes (`/health`), it must be updated in all
locations. Keep health check logic stateless and fast — it is called on every deploy verification
and by Docker's built-in health monitor.

---

## 7. Commit SHA as Image Tag for Traceability

Both CI and CD pipelines derive the image tag by truncating `github.sha` to 7 characters:
- `ci.yml:80-81` builds and pushes `<ECR>/<repo>:<sha7>` + `:latest`
- `cd.yml:55-60` derives the same tag for the SSM `docker run` command

The `:latest` tag is always overwritten; the SHA tag is immutable and provides full commit
traceability for every running container (visible via the `APP_VERSION` env var at runtime).

**Implication:** Never deploy by referencing `:latest` in production — always use the SHA tag.
The CD pipeline does this automatically via the `image-uri` output from the CI job.

---

## 8. EC2 user_data Bootstrap (Self-Configuring Instance)

`terraform/main.tf:139-165` uses `user_data` to run a shell script exactly once on first boot.
The script installs Docker, authenticates against ECR, and starts the application container with
`--restart unless-stopped`. This means the instance is fully operational without any manual
post-provisioning steps.

**Implication:** `user_data` only runs on the first boot. If the script needs to change,
the instance must be recreated (not just rebooted). Use SSM commands for runtime updates;
`user_data` is for initial bootstrap only.

---

## 9. SSM-Based Remote Execution (No SSH)

`cd.yml:89-116` sends `docker pull` + `docker run` commands to the EC2 instance using
`aws ssm send-command` with the `AWS-RunShellScript` document. This requires:
- The instance to have the `AmazonSSMManagedInstanceCore` IAM policy (attached at `main.tf:73-76`)
- The SSM Agent running on the instance (pre-installed on Amazon Linux 2023)
- No inbound port 22 open in the Security Group

**Implication:** Never add SSH key pairs or open port 22 to the security group. All remote
operations must go through SSM. Access is governed by IAM, not network rules.

---

## 10. CI/CD Job Dependency Chain

Both pipelines enforce a strict gate via `needs:`:
- `ci.yml:64`: `build-and-push` requires `test` to pass
- `cd.yml:34`: `deploy` requires manual approval via GitHub's `environment: production`
  protection rules

**Implication:** You cannot bypass tests by re-running only downstream jobs. The `production`
environment approval gate must be configured in GitHub repository settings under
**Settings → Environments → production**.
