# Architectural Patterns

Patterns that appear across multiple files and inform how this project is structured.

---

## 1. Terraform Module Composition (VPC → EKS → ECR)

`terraform/main.tf:9-72` composes three official `terraform-aws-modules` in dependency order:
VPC is provisioned first, then EKS references `module.vpc.vpc_id` and
`module.vpc.private_subnets`, then ECR is independent. All three are community registry modules
(not custom), which means their internal behavior is governed by the module versions pinned in
`source` + `version` constraints (`~> 5.0`, `~> 20.0`).

**Implication:** When adding new AWS resources, prefer official modules over raw `resource` blocks
where one exists. Pin with `~>` (pessimistic constraint) to allow patch updates but not majors.

---

## 2. Environment Parameterization with Validation

All environment-specific values flow through `terraform/variables.tf`. The `environment` variable
enforces an allowlist (`dev | staging | prod`) via a `validation` block at `variables.tf:19-23`.
The same environment value propagates to:
- AWS resource tags via `provider.tf:40`
- EKS node labels via `main.tf:64`
- Helm deployment via `cd.yml:112`
- Container env var `ENVIRONMENT` at runtime via `app/main.py:21`

**Implication:** Never hard-code `dev`/`prod` strings in resource definitions. Pass through
`var.environment` or `{{ .Values.env.ENVIRONMENT }}`.

---

## 3. Remote State with Distributed Locking

`terraform/provider.tf:23-29` stores state in S3 (`smartcampus-terraform-state`) and uses
DynamoDB (`smartcampus-terraform-locks`) for lock management. Both the bucket and table must
exist before `terraform init` can succeed — they are prerequisite manual resources (not managed
by this Terraform code itself).

**Implication:** The S3 bucket and DynamoDB table are bootstrapped outside this codebase.
Do not add them to `main.tf` — circular dependency.

---

## 4. Global Resource Tagging via Provider Default Tags

`terraform/provider.tf:37-44` applies `Project`, `Environment`, `ManagedBy`, and `Owner` tags
to every AWS resource created by the provider — without any per-resource `tags` blocks needed.
Individual resources only add tags when they need resource-specific ones.

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
- Kubernetes liveness probe at `helm/smartcampus/values.yaml:49-50`
- Kubernetes readiness probe at `helm/smartcampus/values.yaml:57-58`
- Helm deployment template at `helm/smartcampus/templates/deployment.yaml:82-93`

**Implication:** If the health endpoint path changes (`/health`), it must be updated in all four
locations. Keep health check logic stateless and fast — it is called every 10-30 seconds.

---

## 7. Commit SHA as Image Tag for Traceability

Both CI and CD pipelines derive the image tag by truncating `github.sha` to 7 characters:
- `ci.yml:80-81` builds and pushes `<ECR>/<repo>:<sha7>` + `:latest`
- `cd.yml:99-100` derives the same tag for `helm upgrade --set image.tag=<sha7>`

The `:latest` tag is always overwritten; the SHA tag is immutable and provides full commit
traceability for every running pod (visible via the `version` label in `deployment.yaml:43`).

**Implication:** Never deploy by referencing `:latest` in production — always use the SHA tag
via `--set image.tag=`. The pipeline does this automatically.

---

## 8. Helm Values Injection at Deploy Time (not baked in)

`helm/smartcampus/values.yaml:11` leaves `image.repository` empty (`""`). The actual ECR URL
is injected at deploy time via `--set image.repository=...` in `cd.yml:110`. This means:
- The chart is registry-agnostic and portable
- The same chart can deploy to any ECR URL or even a different registry

**Implication:** Never commit a real ECR URL into `values.yaml`. The CI/CD pipeline is the only
place where the registry URL is materialized.

---

## 9. Zero-Downtime Rolling Updates

`helm/smartcampus/values.yaml:63-67` configures `maxUnavailable: 0` and `maxSurge: 1`. Combined
with `minReplicas: 2` in the HPA, this guarantees at least 2 healthy pods serving traffic at
all times during a rollout. The `--atomic` flag in `cd.yml:113` auto-rolls back if the deploy
fails to reach `Ready` within the timeout.

**Implication:** The minimum replica count and rolling update settings are coupled — reducing
`minReplicas` to 1 with `maxUnavailable: 0` would still briefly leave only 1 pod.

---

## 10. Topology Spread Constraints for Node Distribution

`helm/smartcampus/templates/deployment.yaml:50-56` uses `topologySpreadConstraints` with
`topologyKey: kubernetes.io/hostname` and `whenUnsatisfiable: DoNotSchedule`. This forces
the scheduler to distribute pods across different EC2 nodes, preventing all pods from landing
on the same node.

**Implication:** This constraint requires at least as many schedulable nodes as `minReplicas`.
If the cluster has only 1 node, pods beyond the first will stay `Pending`.

---

## 11. ConfigMap Checksum Annotation for Automatic Redeploys

`helm/smartcampus/templates/deployment.yaml:46` adds a pod annotation:
```
checksum/config: {{ include ... | sha256sum }}
```
This embeds a hash of the ConfigMap content into the pod spec. Helm detects the annotation
change as a pod template mutation, triggering a rolling restart whenever `configmap.yaml`
changes — even if the image tag did not change.

**Implication:** Configuration changes propagate automatically on the next `helm upgrade`.
No manual `kubectl rollout restart` needed.

---

## 12. CI/CD Job Dependency Chain

Both pipelines enforce a strict gate via `needs:`:
- `ci.yml:64`: `build-and-push` requires `test` to pass
- `cd.yml:60`: `deploy` requires `validate-helm` to pass, and `deploy` additionally
  requires manual approval via GitHub's `environment: production` protection rules (`cd.yml:61`)

**Implication:** You cannot bypass tests or Helm validation by re-running only downstream jobs.
The `production` environment approval gate must be configured in GitHub repository settings.
