# Nest Kubernetes Helm Chart - Comprehensive Summary

## Overview

A production-ready Helm v3 chart for deploying the Nest multi-language networking and infrastructure platform on Kubernetes. The chart provides enterprise-grade deployment configurations with support for development, staging, and production environments.

## Chart Structure

```
k8s/helm/nest/
├── Chart.yaml                     # Chart metadata (version: 1.0.0)
├── values.yaml                    # Default base values
├── values-dev.yaml                # Development environment overrides
├── values-staging.yaml            # Staging environment overrides
├── values-prod.yaml               # Production environment overrides
└── templates/                     # Kubernetes templates
    ├── _helpers.tpl              # Helm helper functions and macros
    ├── deployment.yaml           # Main Flask/Python application
    ├── service.yaml              # Service for app exposure
    ├── ingress.yaml              # Ingress controller configuration
    ├── configmap.yaml            # Application configuration
    ├── secret.yaml               # Secrets management (passwords, keys)
    ├── serviceaccount.yaml       # RBAC and service account
    ├── servicemonitor.yaml       # Prometheus metrics collection
    ├── hpa.yaml                  # Horizontal Pod Autoscaler
    ├── networkpolicy.yaml        # Network policies
    ├── poddisruptionbudget.yaml # High availability
    ├── pvc.yaml                  # Persistent volume claims
    └── external-secrets-example.yaml # External secrets operator examples
```

## Key Features

### 1. Application Deployment (`deployment.yaml`)
- Multi-replica Flask/Python application
- Health checks: liveness and readiness probes
- Resource management: CPU/memory limits and requests
- Security context: non-root user (UID 1000), read-only filesystem
- Volume mounts: temporary and cache directories
- Environment variable injection from ConfigMaps and Secrets
- Graceful shutdown with 30-second termination grace period

### 2. Configuration Management
- **ConfigMap**: Non-sensitive application configuration
  - Flask environment settings
  - Log levels
  - Database connection details (host, port, name)
  - Cache configuration
  - License server URL
  - Monitoring settings
  - Security settings (CORS, TLS)

- **Secret**: Sensitive data (auto-generated with fallback)
  - Database credentials
  - Cache passwords
  - License API keys
  - Application secret keys

### 3. Database Support (`values.yaml`)
- **Default**: PostgreSQL (configurable)
- **Alternatives**: MySQL/MariaDB with Galera support
- **Mode**: External database by default
- **Credentials**: Managed via Kubernetes Secrets
- **Initialization**: SQLAlchemy for schema creation, PyDAL for operations

Example configuration:
```yaml
database:
  type: postgresql
  externalConnection:
    host: postgres.prod.svc.cluster.local
    port: 5432
    database: nest_prod
    username: nest_user
```

### 4. Caching Layer
- **Technology**: Redis/Valkey
- **Mode**: External connection by default
- **Features**: Optional TLS, password authentication
- **Configuration**: Host, port, TLS settings via ConfigMap/Secret

### 5. Networking & Ingress (`ingress.yaml`)
- NGINX ingress controller support
- TLS/SSL with cert-manager integration
- Configurable domains per environment
- Rate limiting (production)
- Automatic HTTP to HTTPS redirect

Production example:
```yaml
ingress:
  hosts:
    - host: nest.penguintech.io
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nest-prod-tls
      hosts:
        - nest.penguintech.io
```

### 6. Monitoring & Observability (`servicemonitor.yaml`)
- **Prometheus Integration**: ServiceMonitor resource
- **Metrics Path**: `/metrics` endpoint
- **Scrape Interval**: 30 seconds (configurable)
- **Auto-discovery**: Pod and node labels for Prometheus
- **Grafana**: Dashboard support ready

### 7. Network Security (`networkpolicy.yaml`)
- Production-grade network policies (Ingress/Egress)
- Ingress from NGINX controller
- Egress to database (5432), cache (6379), DNS (53)
- Production environment: all policies enabled
- Development environment: policies disabled for ease of testing

### 8. High Availability
- **HPA** (`hpa.yaml`): Horizontal Pod Autoscaler
  - Development: disabled (1 replica)
  - Staging: 2-5 replicas (80% CPU/Memory target)
  - Production: 3-10 replicas (70% CPU/Memory target)

- **PDB** (`poddisruptionbudget.yaml`): Pod Disruption Budget
  - Development: disabled
  - Staging: minAvailable: 1
  - Production: minAvailable: 2

### 9. Security & RBAC (`serviceaccount.yaml`)
- Dedicated service account with minimal permissions
- Pod security context: non-root execution
- Read-only root filesystem
- No privilege escalation
- Capabilities restricted (NET_BIND_SERVICE only)

### 10. Persistent Storage (`pvc.yaml`)
- Optional persistent volumes for application data
- Configurable storage class and size
- Development: disabled by default
- Production: can be enabled for state management

## Environment-Specific Configurations

### Development (`values-dev.yaml`)
```
Replicas: 1
Image Tag: latest
Resources: 250m CPU / 256Mi memory
Autoscaling: Disabled
Log Level: DEBUG
Database: nest_dev
Network Policies: Disabled
```

### Staging (`values-staging.yaml`)
```
Replicas: 2
Image Tag: v1.0.0
Resources: 500m CPU / 512Mi memory
Autoscaling: Enabled (2-5)
Log Level: INFO
Database: nest_staging
Network Policies: Enabled
PDB: minAvailable=1
```

### Production (`values-prod.yaml`)
```
Replicas: 3
Image Tag: v1.0.0
Resources: 1000m CPU / 1Gi memory
Autoscaling: Enabled (3-10)
Log Level: WARN
Database: nest_prod
Network Policies: Enabled (strict Ingress/Egress)
PDB: minAvailable=2
TLS: Required (cert-manager)
```

## Values File Configuration

### Core Application Settings

```yaml
app:
  name: nest
  replicaCount: 1
  image:
    repository: penguintech/nest
    tag: "1.0.0"
    pullPolicy: IfNotPresent
  
  service:
    type: ClusterIP
    port: 8000
    targetPort: 8000
  
  resources:
    limits: {cpu: 500m, memory: 512Mi}
    requests: {cpu: 250m, memory: 256Mi}
```

### Database Configuration

```yaml
database:
  type: postgresql          # or mysql/mariadb
  enabled: true
  useExternal: true         # false to deploy PostgreSQL in-cluster
  
  externalConnection:
    host: postgres.default.svc.cluster.local
    port: 5432
    database: nest
    username: nest_user
```

### Cache Configuration

```yaml
cache:
  enabled: true
  useExternal: true         # false to deploy Redis in-cluster
  
  externalConnection:
    host: redis.default.svc.cluster.local
    port: 6379
    tls: false
```

### License Server

```yaml
config:
  license:
    serverUrl: "https://license.penguintech.io"
    enabled: true
    cacheExpiry: 86400      # 24 hours
```

## Helm Template Functions (`_helpers.tpl`)

### Available Macros

- **nest.name**: Chart name
- **nest.fullname**: Full application name (release-name-chart-name)
- **nest.chart**: Chart name and version
- **nest.labels**: Common Kubernetes labels
- **nest.selectorLabels**: Pod selector labels
- **nest.serviceAccountName**: Service account name

Usage example:
```yaml
metadata:
  labels:
    {{- include "nest.labels" . | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "nest.selectorLabels" . | nindent 6 }}
```

## External Secrets Integration

For production secret management, the chart includes examples for:

1. **AWS Secrets Manager**: Via IAM roles/IRSA
2. **HashiCorp Vault**: Via Kubernetes auth
3. **Azure Key Vault**: Via Managed Identity
4. **Google Cloud Secret Manager**: Via Workload Identity

See `external-secrets-example.yaml` for detailed implementations.

## Deployment Examples

### Development Cluster
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-dev.yaml \
  -n nest-dev \
  --create-namespace
```

### Production with Custom Database
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  --set database.externalConnection.host=my-postgres.example.com \
  --set database.externalConnection.password=$(kubectl get secret db-creds -o jsonpath='{.data.password}' | base64 -d) \
  -n nest-prod
```

### Production with Sealed Secrets
```bash
# Create sealed secret
echo '{"database-password":"mypassword"}' | kubeseal -f - -w sealed-secret.json

# Install with sealed secret
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -f ./sealed-secret.json \
  -n nest-prod
```

## Kubernetes Version Requirements

- **Minimum**: v1.24
- **Recommended**: v1.25+ (latest stable)
- **Features Used**:
  - Deployment, StatefulSet, Service (v1)
  - Ingress (networking.k8s.io/v1)
  - NetworkPolicy (networking.k8s.io/v1)
  - HPA v2 (autoscaling/v2)
  - PDB v1 (policy/v1)
  - ServiceMonitor (monitoring.coreos.com/v1)

## Performance Tuning

### Development
- Single replica, small resources
- Debug logging enabled
- No autoscaling

### Staging
- 2 replicas, medium resources
- Info logging
- Autoscaling enabled (2-5)

### Production
- 3 replicas, large resources
- Warning logging
- Autoscaling enabled (3-10)
- Pod Disruption Budget: min 2
- Network policies: strict enforcement
- Prometheus monitoring enabled

## Best Practices Implemented

1. **Resource Management**: CPU and memory limits/requests
2. **Health Checks**: Liveness and readiness probes
3. **Security**: Non-root user, read-only filesystem, no privilege escalation
4. **High Availability**: Multiple replicas, HPA, PDB
5. **Monitoring**: Prometheus ServiceMonitor, structured logging
6. **Configuration**: ConfigMap for non-secrets, Secret for sensitive data
7. **RBAC**: Dedicated service account with minimal permissions
8. **Network Policies**: Restrict Ingress/Egress in production
9. **Graceful Shutdown**: 30-second termination grace period
10. **Version Control**: All manifests template-driven and DRY

## Customization

### Add Custom ConfigMap Values
```yaml
# Edit values.yaml
config:
  custom:
    myKey: "myValue"
```

### Override Image Registry
```bash
helm install nest ./k8s/helm/nest \
  --set app.image.repository=myregistry.azurecr.io/nest
```

### Enable Persistence
```bash
helm install nest ./k8s/helm/nest \
  --set app.persistence.enabled=true \
  --set app.persistence.size=50Gi
```

## Troubleshooting Commands

```bash
# Check Helm values
helm values nest -n nest-prod

# Validate chart
helm lint ./k8s/helm/nest

# Dry-run installation
helm install nest ./k8s/helm/nest \
  --dry-run --debug \
  -f ./k8s/helm/nest/values-prod.yaml

# View rendered templates
helm template nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml

# Check deployment status
kubectl rollout status deployment/nest -n nest-prod
```

## Support & Documentation

- **Full Guide**: See `README.md`
- **Quick Start**: See `INSTALL.md`
- **Quick Reference**: See `QUICK_REFERENCE.md`
- **License**: Limited AGPL-3.0 (see LICENSE.md)
- **Support**: support@penguintech.io
