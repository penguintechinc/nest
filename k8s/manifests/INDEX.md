# Nest Kubernetes Manifests - Index

## Quick Reference

### All Manifests at a Glance

| File | Size | Purpose | Environments |
|------|------|---------|--------------|
| **00-namespace.yaml** | 372 B | Creates 3 namespaces | dev, staging, prod |
| **10-configmap.yaml** | 2.9 KB | App configuration | dev, staging, prod |
| **11-secrets.yaml** | 1.7 KB | Sensitive credentials | dev, staging, prod |
| **20-postgres-statefulset.yaml** | 7.3 KB | PostgreSQL database | dev, staging, prod |
| **21-postgres-service.yaml** | 919 B | DB service endpoints | dev, staging, prod |
| **30-redis-deployment.yaml** | 5.9 KB | Redis cache layer | dev, staging, prod |
| **31-redis-service.yaml** | 829 B | Cache service endpoints | dev, staging, prod |
| **40-app-deployment.yaml** | 11 KB | Main application | dev, staging, prod |
| **41-app-service.yaml** | 871 B | App service endpoints | dev, staging, prod |
| **50-ingress.yaml** | 1.8 KB | HTTP/HTTPS ingress | dev, staging, prod |
| **60-servicemonitor.yaml** | 2.7 KB | Prometheus monitoring | dev, staging, prod |
| **deploy.sh** | 7.2 KB | Deployment automation | N/A |
| **README.md** | 11 KB | Full documentation | N/A |

**Total: 54.8 KB across 13 files and 1,940 lines of YAML/Bash**

## Deployment Order

When deploying, apply manifests in this order:

```
1. 00-namespace.yaml        (Create namespaces)
2. 10-configmap.yaml        (Configuration)
3. 11-secrets.yaml          (Credentials)
4. 20-postgres-*.yaml       (Database infrastructure)
5. 30-redis-*.yaml          (Cache infrastructure)
6. 40-app-*.yaml            (Application deployment)
7. 50-ingress.yaml          (External access)
8. 60-servicemonitor.yaml   (Monitoring)
```

## Key Components

### Infrastructure Layer
- **PostgreSQL**: Stateful database with persistent storage
- **Redis**: In-memory cache with persistence
- Both include environment-specific resource sizing

### Application Layer
- **Deployment**: Multi-replica application servers
- **Service**: Internal load balancing
- **Ingress**: External HTTPS access with TLS

### Observability Layer
- **ServiceMonitor**: Prometheus metrics scraping
- **Health checks**: Liveness and readiness probes
- **Logging**: Structured logging to stdout/stderr

## Resource Specifications

### Development Environment (nest-dev)
```
nest-app:           1 replica,   256Mi RAM,  250m CPU
PostgreSQL:         1 StatefulSet, 10Gi storage
Redis:              1 Deployment,   5Gi storage
```

### Staging Environment (nest-staging)
```
nest-app:           2 replicas,  512Mi RAM,  500m CPU
PostgreSQL:         1 StatefulSet, 20Gi storage
Redis:              1 Deployment,  10Gi storage
```

### Production Environment (nest-prod)
```
nest-app:           3 replicas,    1Gi RAM,    1 CPU (pod anti-affinity)
PostgreSQL:         1 StatefulSet, 50Gi storage
Redis:              1 Deployment,  20Gi storage (LRU eviction)
```

## Namespace Structure

Each namespace contains:
- 1 ConfigMap (nest-config)
- 1 Secret (nest-secrets)
- 1 PostgreSQL StatefulSet + Service
- 1 Redis Deployment + Service
- 1 Application Deployment + Service
- 1 Ingress
- 3 ServiceMonitors (app, postgres, redis)

## Environment Variables

### From ConfigMap
- Database connection settings
- API port and configuration
- Logging levels
- Feature flags
- Performance tuning parameters

### From Secrets
- Database credentials
- Redis passwords
- License keys
- JWT secrets
- SMTP credentials

All application pods receive these via:
- `valueFrom.configMapKeyRef` for non-sensitive config
- `valueFrom.secretKeyRef` for sensitive data

## Health Checks

All containers include probes:

**Liveness Probe**: Restarts unhealthy pods
- App: HTTP GET /health every 10s
- Database: pg_isready every 10s
- Cache: redis-cli ping every 10s

**Readiness Probe**: Removes from load balancer if not ready
- App: HTTP GET /health every 5s
- Database: pg_isready every 5s
- Cache: redis-cli ping every 5s

## Storage & Persistence

### PostgreSQL Storage
```yaml
spec:
  volumeClaimTemplates:
  - spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 10Gi/20Gi/50Gi
```

### Redis Storage
```yaml
volumes:
- name: redis-storage
  persistentVolumeClaim:
    claimName: redis-pvc
```

Both use PVC for persistent, reliable storage across pod restarts.

## Networking

### Service Discovery
- PostgreSQL: `postgres:5432` (headless service)
- Redis: `redis:6379` (ClusterIP service)
- App: `nest-app:8080` (ClusterIP service)

### Ingress Routing
- Development: `api-dev.example.com` → nest-app:8080
- Staging: `api-staging.example.com` → nest-app:8080
- Production: `api.example.com` → nest-app:8080

All use HTTPS with Let's Encrypt certificates (staging and prod).

## Monitoring

### Prometheus Endpoints
- **Application**: `/metrics` on port 8080
- **PostgreSQL**: `/metrics` (requires postgres_exporter)
- **Redis**: `/metrics` (requires redis_exporter)

### Metrics Scraped Every 30 Seconds
ServiceMonitor configuration enables Prometheus to automatically discover and scrape metrics.

Requires: Prometheus Operator + Prometheus instance

## Deployment Methods

### Automated (Recommended)
```bash
./deploy.sh dev apply      # Deploy dev
./deploy.sh staging apply  # Deploy staging
./deploy.sh prod apply     # Deploy prod
```

### Manual
```bash
kubectl apply -f 00-namespace.yaml
kubectl apply -f 10-configmap.yaml
# ... etc
```

### Namespace-Specific
```bash
kubectl apply -f . -n nest-dev
```

## Customization Checklist

Before deploying, update:

- [ ] `11-secrets.yaml`: Database passwords, license key, secrets
- [ ] `50-ingress.yaml`: Domain names for your environment
- [ ] `40-app-deployment.yaml`: Container image repository/tag
- [ ] Storage classes (if not using defaults)
- [ ] Resource requests/limits (if different cluster specs)
- [ ] Replica counts (if different HA requirements)

## Troubleshooting Quick Links

See `README.md` sections:
- Pod stuck in Pending
- Database connection failures
- Certificate issues with Ingress
- Redis authentication errors
- Storage issues

## File Descriptions

### 00-namespace.yaml
Three Kubernetes Namespace objects with environment labels. Required for isolation and multi-tenancy. Must be applied first.

### 10-configmap.yaml
ConfigMap data for all three environments. Includes database URLs, API ports, logging levels, and other non-sensitive configuration. Update password placeholders with actual credentials or remove them.

### 11-secrets.yaml
Kubernetes Secret objects containing sensitive data. Template includes placeholders marked with `CHANGE_ME_*`. Must be customized with actual credentials before deployment.

### 20-postgres-statefulset.yaml
PostgreSQL 15 Alpine StatefulSet with:
- 3 separate specs (one per environment)
- Environment-specific storage sizing (10Gi/20Gi/50Gi)
- PersistentVolume claims for data persistence
- Health checks via pg_isready
- Init command for UTF-8 encoding compatibility

### 21-postgres-service.yaml
Headless Service (clusterIP: None) for PostgreSQL StatefulSet. Enables direct pod DNS resolution and ordered deployment.

### 30-redis-deployment.yaml
Redis 7 Alpine Deployment with:
- 3 separate specs (one per environment)
- Password authentication from secrets
- Persistence enabled (AOF, appendfsync=everysec)
- Production includes maxmemory and LRU eviction policy
- Health checks via redis-cli ping

### 31-redis-service.yaml
ClusterIP Service for Redis Deployment. Provides stable internal endpoint across pod restarts.

### 40-app-deployment.yaml
Main Nest application Deployment with:
- 3 separate specs (1/2/3 replicas for dev/staging/prod)
- Production includes pod anti-affinity
- Init containers waiting for PostgreSQL and Redis
- Full environment variable injection from ConfigMap and Secrets
- HTTP health checks (liveness and readiness)
- Environment-specific resource requests/limits

### 41-app-service.yaml
ClusterIP Service exposing port 8080 for the application. Three copies (one per namespace) enable consistent service discovery across environments.

### 50-ingress.yaml
HTTPS Ingress with:
- 3 separate rules (one per environment)
- TLS certificate provisioning via cert-manager
- Environment-specific hostnames
- Production includes rate limiting annotation
- Path-based routing to nest-app service

### 60-servicemonitor.yaml
Prometheus ServiceMonitor resources for three components:
- **nest-app**: Scrapes application metrics from /metrics
- **postgres**: Scrapes database metrics (requires postgres_exporter)
- **redis**: Scrapes cache metrics (requires redis_exporter)

Three copies (one per environment) enable monitoring across all namespaces. Requires Prometheus Operator to be installed.

### deploy.sh
Bash script automating deployment with:
- Prerequisites checking (kubectl, cluster connectivity)
- Manifest validation (dry-run)
- Ordered deployment
- Rollout status monitoring
- Status reporting
- Deletion with safety prompts
- Color-coded output

### README.md
Comprehensive documentation including:
- Quick start guide
- Complete deployment steps
- Configuration options
- Monitoring setup
- Troubleshooting guide
- Security best practices
- Advanced topics (HPA, PDB, etc.)

## Statistics

- **Total Files**: 13
- **Total Size**: 54.8 KB
- **YAML Lines**: ~1,500
- **Script Lines**: ~440
- **Documentation Lines**: ~1,300
- **Total Configurations**: 11 unique resources × 3 environments
- **Unique Kubernetes Objects**: ~30+

## Support References

### Official Kubernetes Documentation
- https://kubernetes.io/docs/

### Key Concepts Used
- StatefulSets: Database ordering and stable identity
- Deployments: Stateless application replicas
- Services: Service discovery and load balancing
- Ingress: External HTTP(S) routing
- PersistentVolumes: Storage persistence
- ConfigMaps: Configuration management
- Secrets: Sensitive data storage
- Probes: Health and readiness checking

### Tool References
- kubectl cheat sheet: https://kubernetes.io/docs/reference/kubectl/cheatsheet/
- Prometheus Operator: https://prometheus-operator.dev/
- cert-manager: https://cert-manager.io/docs/

## License

These manifests follow the Nest project license. See LICENSE.md in the project root.

---

**Created**: January 9, 2025
**Version**: 1.0.0
**Maintainer**: Penguin Tech Inc
