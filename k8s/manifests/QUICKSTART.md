# Kustomize Quick Start

## Deploy with Kustomize (Recommended)

```bash
# Deploy to development
./deploy.sh dev apply --method kustomize

# Deploy to staging
./deploy.sh staging apply --method kustomize

# Deploy to production
./deploy.sh prod apply --method kustomize
```

## Preview Changes

Before deploying, preview the rendered manifests:

```bash
# See exactly what will be deployed to dev
kubectl kustomize overlays/dev

# Pipe to a file for review
kubectl kustomize overlays/staging > staging-manifest.yaml
```

## Validate Configuration

```bash
# Dry-run validation
./deploy.sh dev validate --method kustomize

# All environments
for env in dev staging prod; do
  ./deploy.sh $env validate --method kustomize
done
```

## Configuration Differences

| Config | Dev | Staging | Prod |
|--------|-----|---------|------|
| Namespace | nest-dev | nest-staging | nest-prod |
| Replicas | 1 | 2 | 3 |
| CPU Request | 250m | 500m | 1000m |
| Memory Request | 256Mi | 512Mi | 1Gi |
| CPU Limit | 500m | 1000m | 2000m |
| Memory Limit | 512Mi | 1Gi | 2Gi |
| DB Storage | 10Gi | 20Gi | 50Gi |
| Cache Storage | 5Gi | 10Gi | 20Gi |
| GIN_MODE | debug | release | release |
| LOG_LEVEL | info | warn | error |
| Domain | api-dev.example.com | api-staging.example.com | api.example.com |

## Directory Structure

```
manifests/
├── base/                    # Generic, environment-agnostic configuration
│   ├── kustomization.yaml
│   └── *.yaml
├── overlays/
│   ├── dev/kustomization.yaml      # Dev-specific patches
│   ├── staging/kustomization.yaml  # Staging-specific patches
│   └── prod/kustomization.yaml     # Prod-specific patches
├── deploy.sh               # Updated deployment script
├── KUSTOMIZE.md           # Detailed guide
└── QUICKSTART.md          # This file
```

## Common Tasks

### Check deployment status
```bash
./deploy.sh dev status
```

### Delete deployment
```bash
./deploy.sh dev delete --method kustomize
```

### Customize configuration
Edit the appropriate overlay in `overlays/{env}/kustomization.yaml` and modify the patch values.

## Traditional kubectl Method (Legacy)

To use the original method without Kustomize:

```bash
./deploy.sh dev apply              # Omit --method kustomize
./deploy.sh staging apply
./deploy.sh prod apply
```

## Further Reading

See `KUSTOMIZE.md` for comprehensive documentation including:
- Detailed patch explanations
- Customization guide
- Troubleshooting
- Advanced Kustomize features
