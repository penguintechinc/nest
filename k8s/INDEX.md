# Nest Kubernetes Deployment - Complete Index

This directory contains a comprehensive, production-ready Kubernetes deployment structure for the Nest networking and infrastructure platform.

## Quick Navigation

### Getting Started
1. **[README.md](./README.md)** - Overview and high-level documentation
2. **[INSTALL.md](./INSTALL.md)** - Quick start installation guide
3. **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Pre-deployment validation checklist

### Helm Chart Documentation
- **[HELM_CHART_SUMMARY.md](./HELM_CHART_SUMMARY.md)** - Complete Helm chart reference
- **Helm Chart Location**: `k8s/helm/nest/`

### Advanced Topics
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Detailed deployment guide
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - Common kubectl and helm commands

## Directory Structure

```
k8s/
├── helm/
│   └── nest/
│       ├── Chart.yaml              # Helm chart metadata (v1.0.0)
│       ├── values.yaml             # Default values (dev baseline)
│       ├── values-dev.yaml         # Development environment
│       ├── values-staging.yaml     # Staging environment
│       ├── values-prod.yaml        # Production environment
│       └── templates/
│           ├── _helpers.tpl        # Helm template functions
│           ├── deployment.yaml     # Flask application deployment
│           ├── service.yaml        # Kubernetes Service
│           ├── ingress.yaml        # Ingress configuration
│           ├── configmap.yaml      # Configuration management
│           ├── secret.yaml         # Secrets management
│           ├── serviceaccount.yaml # RBAC setup
│           ├── servicemonitor.yaml # Prometheus integration
│           ├── hpa.yaml            # Horizontal Pod Autoscaler
│           ├── networkpolicy.yaml  # Network policies
│           ├── poddisruptionbudget.yaml  # High availability
│           ├── pvc.yaml            # Persistent volume claims
│           └── external-secrets-example.yaml  # External secrets examples
│
├── management/        # (Existing cluster management resources)
│   ├── 00-namespace.yaml
│   ├── 01-rbac.yaml
│   ├── 10-dashboard.yaml
│   ├── 20-monitoring.yaml
│   ├── 30-logging.yaml
│   └── 40-41-cronjobs.yaml
│
├── storage/          # (Existing storage resources)
│   ├── storageclass-*.yaml
│   └── pvc-*.yaml
│
├── manifests/        # (Existing manifest resources)
│   └── Various YAML files for alternative deployment
│
└── Documentation
    ├── README.md                      # Start here for overview
    ├── INSTALL.md                     # Quick start guide
    ├── HELM_CHART_SUMMARY.md         # Helm chart reference
    ├── DEPLOYMENT_GUIDE.md           # Detailed deployment
    ├── DEPLOYMENT_CHECKLIST.md       # Pre-deployment checklist
    ├── QUICK_REFERENCE.md            # Command reference
    └── INDEX.md                       # This file
```

## Key Features

### Application Deployment
- Multi-replica Flask/Python application
- Health checks (liveness and readiness probes)
- Resource limits and requests
- Security context (non-root, read-only filesystem)
- Graceful shutdown handling

### Database & Cache
- PostgreSQL support (MySQL/MariaDB configurable)
- Redis/Valkey cache integration
- External database connections
- Credential management via Kubernetes Secrets

### Networking
- NGINX Ingress controller support
- TLS/SSL with cert-manager
- Network policies for security
- Service exposure and load balancing

### Monitoring & Observability
- Prometheus ServiceMonitor integration
- Application metrics endpoint (/metrics)
- Structured logging with configurable levels
- Grafana dashboard readiness

### High Availability
- Horizontal Pod Autoscaler (HPA)
- Pod Disruption Budget (PDB)
- Multiple replicas in production
- Health probes configuration

### Security
- Pod security context
- Network policies (Ingress/Egress)
- Secrets management
- RBAC via ServiceAccount
- Non-root container execution

## Environment Configurations

### Development
- Single replica
- Latest image tag
- Debug logging
- No autoscaling
- Minimal resources

### Staging
- 2 replicas
- Versioned image tag
- Info logging
- Autoscaling enabled (2-5)
- Medium resources

### Production
- 3 replicas
- Versioned image tag
- Warning logging
- Autoscaling enabled (3-10)
- Full resources
- Strict network policies
- PDB with minAvailable: 2

## Getting Started

### 1. Prerequisites
```bash
# Ensure you have:
- Kubernetes cluster v1.24+
- kubectl configured
- helm v3.0+
- NGINX ingress controller
- cert-manager (optional but recommended)
```

### 2. Validate Helm Chart
```bash
helm lint ./k8s/helm/nest
helm template nest ./k8s/helm/nest -f ./k8s/helm/nest/values-prod.yaml
```

### 3. Deploy
```bash
# Development
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-dev.yaml \
  -n nest-dev \
  --create-namespace

# Production
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -n nest-prod \
  --create-namespace
```

### 4. Verify
```bash
kubectl get all -n nest-prod
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=nest -n nest-prod
kubectl logs -f -n nest-prod -l app.kubernetes.io/name=nest
```

## Common Tasks

### Port Forward to Application
```bash
kubectl port-forward svc/nest 8000:8000 -n nest-prod
curl http://localhost:8000/health
```

### View Logs
```bash
kubectl logs -f -n nest-prod -l app.kubernetes.io/name=nest
```

### Scale Manually
```bash
kubectl scale deployment nest -n nest-prod --replicas=5
```

### Update Image
```bash
kubectl set image deployment/nest \
  nest=penguintech/nest:v1.1.0 \
  -n nest-prod
```

### Monitor HPA
```bash
kubectl get hpa -n nest-prod -w
```

### Check Metrics
```bash
kubectl top pods -n nest-prod
kubectl top nodes
```

## Documentation Guides

### For Quick Start
Start with: **[INSTALL.md](./INSTALL.md)**

### For Full Understanding
Read: **[README.md](./README.md)**

### For Helm Chart Details
Consult: **[HELM_CHART_SUMMARY.md](./HELM_CHART_SUMMARY.md)**

### For Pre-Deployment
Use: **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)**

### For Commands Reference
See: **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)**

### For Detailed Deployment
Follow: **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**

## Helm Chart Files

All Helm chart files are located in `/home/penguin/code/Nest/k8s/helm/nest/`

### Values Files
- `values.yaml` - Default values (development baseline)
- `values-dev.yaml` - Development environment overrides
- `values-staging.yaml` - Staging environment overrides
- `values-prod.yaml` - Production environment overrides

### Templates (in `templates/` subdirectory)
- `_helpers.tpl` - Helm template helper functions
- `deployment.yaml` - Flask application deployment
- `service.yaml` - Service resource
- `ingress.yaml` - Ingress configuration
- `configmap.yaml` - Application configuration
- `secret.yaml` - Secrets (passwords, API keys)
- `serviceaccount.yaml` - RBAC setup
- `servicemonitor.yaml` - Prometheus metrics
- `hpa.yaml` - Horizontal Pod Autoscaler
- `networkpolicy.yaml` - Network policies
- `poddisruptionbudget.yaml` - High availability
- `pvc.yaml` - Persistent volume claims
- `external-secrets-example.yaml` - External secrets examples

## Configuration Reference

### Database Configuration
```yaml
database:
  type: postgresql  # postgresql, mysql, mariadb
  externalConnection:
    host: postgres.example.com
    port: 5432
    database: nest_prod
    username: nest_user
```

### Cache Configuration
```yaml
cache:
  externalConnection:
    host: redis.example.com
    port: 6379
    tls: false
```

### License Server
```yaml
config:
  license:
    serverUrl: "https://license.penguintech.io"
    enabled: true
```

### Monitoring
```yaml
monitoring:
  prometheus:
    serviceMonitor:
      enabled: true
      interval: 30s
```

## Technology Stack

- **Kubernetes**: v1.24+
- **Helm**: v3.0+
- **Container Runtime**: Docker/Containerd
- **Ingress**: NGINX controller
- **TLS**: cert-manager
- **Monitoring**: Prometheus + Grafana
- **Database**: PostgreSQL (primary)
- **Cache**: Redis/Valkey
- **Application**: Python 3.13 Flask

## Best Practices Implemented

1. **Resource Management**: CPU/memory limits and requests
2. **Health Checks**: Liveness and readiness probes
3. **Security**: Non-root, read-only filesystem, minimal privileges
4. **High Availability**: Replicas, HPA, PDB
5. **Observability**: Prometheus metrics, structured logging
6. **Configuration Management**: ConfigMap and Secret separation
7. **RBAC**: Dedicated service account
8. **Network Security**: Network policies
9. **Graceful Shutdown**: Termination grace period
10. **Version Control**: All manifests template-driven

## Support & Contact

- **Email**: support@penguintech.io
- **License Server**: https://license.penguintech.io
- **Website**: https://www.penguintech.io
- **License**: Limited AGPL-3.0 with commercial use restrictions

## Version Information

- **Helm Chart Version**: 1.0.0
- **Chart App Version**: 1.0.0
- **Kubernetes Minimum**: v1.24
- **Created**: 2026-01-09

---

**Next Step**: Read [README.md](./README.md) for comprehensive deployment documentation.
