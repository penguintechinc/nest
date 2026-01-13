# Kubernetes Deployment Structure for Nest

This directory contains production-ready Kubernetes manifests and Helm charts for deploying the Nest networking and infrastructure platform.

## Directory Structure

```
k8s/
├── helm/
│   └── nest/
│       ├── Chart.yaml              # Helm chart metadata
│       ├── values.yaml             # Default values (dev-oriented)
│       ├── values-dev.yaml         # Development environment overrides
│       ├── values-staging.yaml     # Staging environment overrides
│       ├── values-prod.yaml        # Production environment overrides
│       └── templates/              # Kubernetes templates
│           ├── _helpers.tpl        # Helm helper functions
│           ├── deployment.yaml     # Main Flask application deployment
│           ├── service.yaml        # Kubernetes Service
│           ├── ingress.yaml        # Ingress controller configuration
│           ├── configmap.yaml      # Application configuration
│           ├── secret.yaml         # Secrets management
│           ├── serviceaccount.yaml # Service account and RBAC
│           ├── servicemonitor.yaml # Prometheus metrics collection
│           ├── hpa.yaml            # Horizontal Pod Autoscaler
│           ├── networkpolicy.yaml  # Network policies
│           ├── poddisruptionbudget.yaml # Pod disruption budget
│           └── pvc.yaml            # Persistent volume claims
└── README.md                       # This file
```

## Helm Chart Overview

### Chart Information
- **Name**: nest
- **Version**: 1.0.0
- **AppVersion**: 1.0.0
- **Type**: Application chart

### Key Features

#### Application Deployment
- Multi-replica Flask/Python application deployment
- Health checks (liveness and readiness probes)
- Resource limits and requests
- Security context (non-root, read-only filesystem)
- Persistent volume support for data storage

#### Database Support
- Primary: PostgreSQL (configurable to MySQL/MariaDB)
- External database connection by default
- SQLAlchemy for initialization, PyDAL for operations
- Database credentials managed via Kubernetes Secrets

#### Caching Layer
- Redis/Valkey support
- External connection by default
- Optional TLS encryption
- Configurable password authentication

#### Monitoring & Observability
- Prometheus ServiceMonitor for metrics collection
- Application metrics exposed on `/metrics` endpoint
- Pod annotations for Prometheus scraping
- Grafana dashboard support

#### Networking
- Ingress controller integration (NGINX)
- TLS/SSL with cert-manager support
- Network policies for traffic control
- Service for application exposure

#### Security
- Pod Security Context
- Network policies (Ingress/Egress)
- Secrets management
- RBAC via ServiceAccount
- Non-root container execution

#### High Availability
- Horizontal Pod Autoscaler (HPA)
- Pod Disruption Budget
- Multiple replicas in production
- Health probes configuration

## Deployment Instructions

### Prerequisites

1. **Kubernetes Cluster**: v1.24+
2. **Helm**: v3.0+
3. **kubectl**: Installed and configured
4. **Ingress Controller**: NGINX ingress controller (recommended)
5. **Cert-Manager**: For TLS certificate management (optional)
6. **Prometheus Operator**: For monitoring (optional)

### Installation

#### 1. Development Environment

```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-dev.yaml \
  -n nest-dev \
  --create-namespace
```

#### 2. Staging Environment

```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-staging.yaml \
  -n nest-staging \
  --create-namespace
```

#### 3. Production Environment

```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -n nest-prod \
  --create-namespace
```

### Verification

```bash
# Check deployment status
kubectl get deployments -n nest-prod

# Check pods
kubectl get pods -n nest-prod

# Check ingress
kubectl get ingress -n nest-prod

# Check HPA status
kubectl get hpa -n nest-prod

# View pod logs
kubectl logs -n nest-prod -l app.kubernetes.io/name=nest --tail=100
```

## Configuration Management

### Environment Variables

All configuration is managed through:
1. **ConfigMap** (`configmap.yaml`): Non-sensitive configuration
2. **Secret** (`secret.yaml`): Sensitive data (passwords, API keys)

Key environment variables:
- `FLASK_ENV`: Flask environment (development/production)
- `LOG_LEVEL`: Application log level
- `DATABASE_TYPE`: Database type (postgresql/mysql/mariadb)
- `DATABASE_HOST`: Database hostname
- `DATABASE_PORT`: Database port
- `DATABASE_NAME`: Database name
- `DATABASE_USER`: Database username
- `DATABASE_PASSWORD`: Database password
- `CACHE_HOST`: Redis/Valkey hostname
- `CACHE_PORT`: Redis/Valkey port
- `LICENSE_SERVER_URL`: PenguinTech license server URL
- `LICENSE_API_KEY`: License server API key
- `METRICS_ENABLED`: Enable Prometheus metrics

### External Secrets Management

For production deployments, use one of these approaches:

1. **Sealed Secrets**
```bash
kubeseal -f secret.yaml -w sealed-secret.yaml
```

2. **External Secrets Operator**
Create ExternalSecret resources pointing to AWS Secrets Manager, Azure Key Vault, etc.

3. **HashiCorp Vault**
Use Vault agent for secret injection.

## Database Setup

### PostgreSQL Connection

External PostgreSQL example:
```yaml
database:
  type: postgresql
  externalConnection:
    host: postgres.example.com
    port: 5432
    database: nest_prod
    username: nest_user
```

### MySQL/MariaDB Connection

For MariaDB Galera cluster support:
```yaml
database:
  type: mysql
  externalConnection:
    host: mariadb-cluster.example.com
    port: 3306
    database: nest_prod
```

## Monitoring & Metrics

### Prometheus Integration

The ServiceMonitor resource automatically registers the application with Prometheus:
- Scrape interval: 30 seconds
- Metrics path: `/metrics`
- Port: 8000

### Grafana Dashboards

Import dashboards for:
- Application performance metrics
- Flask request/response times
- Database connection pool stats
- Cache hit/miss ratios

## Security Best Practices

1. **Network Policies**: Enable by default in production
2. **Pod Security**: Non-root user (UID 1000)
3. **Secret Management**: Use sealed-secrets or external-secrets-operator
4. **TLS**: Configured with cert-manager
5. **RBAC**: Service account with minimal permissions
6. **Container Security**: Read-only root filesystem, no privilege escalation

## Scaling Configuration

### Development
- Replicas: 1
- HPA: Disabled
- Resource limits: 250m CPU, 256Mi memory

### Staging
- Replicas: 2
- HPA: Enabled (2-5 replicas)
- Target CPU: 80%
- Target Memory: 80%

### Production
- Replicas: 3
- HPA: Enabled (3-10 replicas)
- Target CPU: 70%
- Target Memory: 75%
- Pod Disruption Budget: Minimum 2 available

## Troubleshooting

### Pod not starting
```bash
kubectl describe pod -n nest-prod <pod-name>
kubectl logs -n nest-prod <pod-name>
```

### Database connection issues
```bash
# Check ConfigMap
kubectl get configmap -n nest-prod nest-config -o yaml

# Check Secret (values hidden)
kubectl get secret -n nest-prod nest-secret -o yaml

# Test database connectivity
kubectl run -it --rm debug --image=postgres:16 --restart=Never -- \
  psql -h <host> -U <user> -d <database>
```

### Metrics not appearing
```bash
# Check ServiceMonitor
kubectl get servicemonitor -n nest-prod

# Check Prometheus targets
kubectl port-forward -n prometheus svc/prometheus 9090:9090
# Visit http://localhost:9090/targets
```

## Upgrade Procedure

```bash
# Helm upgrade
helm upgrade nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -n nest-prod

# Verify rollout
kubectl rollout status deployment/nest -n nest-prod

# Rollback if needed
helm rollback nest -n nest-prod
```

## License

This project is licensed under the Limited AGPL-3.0 License with commercial use restrictions.
See LICENSE.md for details.

## Support

For issues, questions, or support:
- **Email**: support@penguintech.io
- **License Server**: https://license.penguintech.io
- **Website**: https://www.penguintech.io
