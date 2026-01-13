# Kustomize Configuration Guide

This directory now supports both traditional kubectl and Kustomize deployment methods.

## Directory Structure

```
manifests/
├── base/                          # Base configuration (generic, environment-agnostic)
│   ├── kustomization.yaml        # Base Kustomization file
│   ├── 00-namespace.yaml
│   ├── 10-configmap.yaml
│   ├── 11-secrets.yaml
│   ├── 20-postgres-*.yaml
│   ├── 21-postgres-service.yaml
│   ├── 30-redis-*.yaml
│   ├── 31-redis-service.yaml
│   ├── 40-app-deployment.yaml
│   ├── 41-app-service.yaml
│   ├── 50-ingress.yaml
│   └── 60-servicemonitor.yaml
│
├── overlays/                      # Environment-specific customizations
│   ├── dev/
│   │   └── kustomization.yaml    # Dev patches: 1 replica, 256Mi/512Mi resources
│   ├── staging/
│   │   └── kustomization.yaml    # Staging patches: 2 replicas, 512Mi/1Gi resources
│   └── prod/
│       └── kustomization.yaml    # Prod patches: 3 replicas, 1Gi/2Gi resources
│
├── deploy.sh                      # Updated script (supports --method flag)
└── KUSTOMIZE.md                   # This file
```

## Key Differences Between Base and Overlays

### Base Configuration
- Single namespace: `nest` (generic)
- Minimal resources
- Standard logging and configuration

### Dev Overlay (nest-dev)
- Namespace: `nest-dev`
- App replicas: 1
- App resources: 256Mi req / 512Mi limit (CPU: 250m/500m)
- Database storage: 10Gi
- Cache storage: 5Gi
- GIN_MODE: debug, LOG_LEVEL: info
- Ingress domain: api-dev.example.com
- TLS issuer: letsencrypt-staging

### Staging Overlay (nest-staging)
- Namespace: `nest-staging`
- App replicas: 2
- App resources: 512Mi req / 1Gi limit (CPU: 500m/1000m)
- Database storage: 20Gi
- Cache storage: 10Gi
- GIN_MODE: release, LOG_LEVEL: warn
- Ingress domain: api-staging.example.com
- TLS issuer: letsencrypt-staging

### Prod Overlay (nest-prod)
- Namespace: `nest-prod`
- App replicas: 3 (with pod anti-affinity)
- App resources: 1Gi req / 2Gi limit (CPU: 1000m/2000m)
- Database storage: 50Gi
- Cache storage: 20Gi
- GIN_MODE: release, LOG_LEVEL: error
- Ingress domain: api.example.com
- TLS issuer: letsencrypt-prod
- imagePullPolicy: Always
- Stricter rolling update strategy (maxUnavailable: 1)

## Deployment Methods

### Option 1: Kustomize (Recommended)

Deploy using Kustomize overlays:

```bash
# Deploy to development
./deploy.sh dev apply --method kustomize

# Deploy to staging
./deploy.sh staging apply --method kustomize

# Deploy to production
./deploy.sh prod apply --method kustomize

# Validate before deploying
./deploy.sh staging validate --method kustomize

# Delete deployment
./deploy.sh prod delete --method kustomize
```

### Option 2: Traditional kubectl

Deploy individual manifests (legacy method):

```bash
# Deploy to development
./deploy.sh dev apply

# Deploy to staging
./deploy.sh staging apply

# Deploy to production
./deploy.sh prod apply
```

## Kustomize Build

To preview what will be deployed:

```bash
# Preview dev deployment
kubectl kustomize overlays/dev

# Preview staging deployment
kubectl kustomize overlays/staging

# Preview prod deployment
kubectl kustomize overlays/prod
```

## Patching Strategy

Each overlay uses strategic merge patches to:

1. **Namespace** - Replace with environment-specific namespace
2. **ConfigMap** - Update GIN_MODE, LOG_LEVEL, DATABASE_URL, CORS_ORIGINS, cache/connection settings
3. **Deployments** - Adjust replica counts and resource limits
4. **StatefulSets** - Adjust replica counts and storage sizes
5. **PersistentVolumeClaims** - Environment-specific storage sizes
6. **Ingress** - Different domains and TLS issuers per environment
7. **All Services** - Update namespace references

## Customization

To modify a patch:

1. Edit the appropriate overlay kustomization.yaml
2. Use JSON Patch operations (op, path, value)
3. Test with `kubectl kustomize overlays/{env}` or `./deploy.sh {env} validate --method kustomize`

Example patch format:
```yaml
- target:
    kind: Deployment
    name: nest-app
  patch: |-
    - op: replace
      path: /spec/replicas
      value: 5
```

## Advantages of Kustomize

- **DRY**: Single base configuration with overlay patches
- **Safe**: Explicit patch-based changes
- **Declarative**: No templating language required
- **Git-friendly**: Easy to review changes per environment
- **Kubernetes-native**: Built into kubectl

## Migration from Old Structure

The old manifests remain in the root of the manifests/ directory for backward compatibility. To fully migrate:

1. Test Kustomize deployment: `./deploy.sh dev apply --method kustomize`
2. Verify all resources deployed correctly
3. Delete old manifests (optional): Remove individual YAML files from manifests/ root
4. Update CI/CD pipelines to use `--method kustomize`

## Troubleshooting

### Patch not applying correctly

Check the resource structure:
```bash
kubectl kustomize overlays/dev | grep -A 10 "kind: Deployment"
```

### Namespace not changing

Verify patch path is correct:
```bash
kubectl kustomize overlays/dev | grep namespace
```

### Resource validation errors

Validate dry-run:
```bash
./deploy.sh staging validate --method kustomize
```

## References

- [Kustomize Documentation](https://kubectl.docs.kubernetes.io/guides/introduction/kustomize/)
- [Strategic Merge Patch](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/declarative-config/#how-apply-calculates-differences)
