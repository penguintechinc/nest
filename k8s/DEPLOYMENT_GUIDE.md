# Nest Kubernetes Deployment Guide

## Overview

Complete kubectl manifest files for deploying the Nest application to Kubernetes across three environments: development, staging, and production.

## What's Included

### Manifest Files (in `/manifests/`)

1. **00-namespace.yaml** (372 bytes)
   - Creates three namespaces: nest-dev, nest-staging, nest-prod
   - Organized by environment with labels

2. **10-configmap.yaml** (2.9 KB)
   - Application configuration for all three environments
   - Database, Redis, API, security, and performance settings
   - Placeholder values for passwords (use secrets instead)

3. **11-secrets.yaml** (1.7 KB)
   - Kubernetes Secret template with required placeholders
   - Database and Redis credentials
   - License key, JWT secret, session secret
   - Must be customized before deployment

4. **20-postgres-statefulset.yaml** (7.3 KB)
   - PostgreSQL 15 Alpine deployment as StatefulSet
   - Persistent storage with environment-specific sizing
   - Environment-specific resource limits and replicas
   - Health checks and proper volume management

5. **21-postgres-service.yaml** (919 bytes)
   - Headless service for PostgreSQL StatefulSet
   - Enables DNS-based service discovery
   - One service per namespace

6. **30-redis-deployment.yaml** (5.9 KB)
   - Redis 7 Alpine deployment with persistence
   - Password authentication configured
   - Environment-specific memory limits and LRU eviction (prod)
   - Health checks via redis-cli

7. **31-redis-service.yaml** (829 bytes)
   - ClusterIP service for Redis
   - Consistent naming across environments

8. **40-app-deployment.yaml** (11 KB)
   - Main Nest application deployment
   - Multi-stage: init containers for service dependencies
   - Environment-specific replicas (1 dev, 2 staging, 3 prod)
   - Pod anti-affinity in production
   - Full environment variable configuration from ConfigMap and Secrets

9. **41-app-service.yaml** (871 bytes)
   - ClusterIP service for application
   - Exposes port 8080

10. **50-ingress.yaml** (1.8 KB)
    - HTTPS ingress with cert-manager integration
    - TLS certificates from Let's Encrypt (staging and prod)
    - Environment-specific hostnames and annotations
    - Production includes rate limiting

11. **60-servicemonitor.yaml** (2.7 KB)
    - Prometheus ServiceMonitor for metrics collection
    - Monitors: nest-app, postgres, redis
    - Deployed across all three environments
    - Requires Prometheus Operator to be installed

### Scripts

- **deploy.sh** - Automated deployment script with validation, status checking, and rollback capabilities

### Documentation

- **README.md** - Comprehensive deployment documentation with troubleshooting
- **DEPLOYMENT_GUIDE.md** - This file

## Quick Start

### Minimal Deployment (Development)

```bash
# 1. Create namespaces
kubectl apply -f manifests/00-namespace.yaml

# 2. Update and apply secrets
# Edit manifests/11-secrets.yaml with your credentials
kubectl apply -f manifests/10-configmap.yaml
kubectl apply -f manifests/11-secrets.yaml

# 3. Deploy infrastructure
kubectl apply -f manifests/20-postgres-statefulset.yaml
kubectl apply -f manifests/21-postgres-service.yaml
kubectl apply -f manifests/30-redis-deployment.yaml
kubectl apply -f manifests/31-redis-service.yaml

# 4. Deploy application
kubectl apply -f manifests/40-app-deployment.yaml
kubectl apply -f manifests/41-app-service.yaml

# 5. Access via port-forward
kubectl port-forward svc/nest-app 8080:8080 -n nest-dev
```

### Automated Deployment

```bash
# Deploy to dev environment
./manifests/deploy.sh dev apply

# Deploy to staging environment
./manifests/deploy.sh staging apply

# Deploy to production environment
./manifests/deploy.sh prod apply
```

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│           Kubernetes Cluster                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────────────────────────────────┐    │
│  │ nest-prod Namespace (Production)      │    │
│  │                                       │    │
│  │  ┌─────────────────────────────────┐ │    │
│  │  │ Ingress (HTTPS/TLS)             │ │    │
│  │  │ - api.example.com               │ │    │
│  │  │ - Rate limiting enabled         │ │    │
│  │  └──────────────┬────────────────┘ │    │
│  │                 │                   │    │
│  │  ┌──────────────▼──────────────┐   │    │
│  │  │ Service: nest-app           │   │    │
│  │  │ Type: ClusterIP             │   │    │
│  │  │ Port: 8080                  │   │    │
│  │  └──────────────┬──────────────┘   │    │
│  │                 │                   │    │
│  │  ┌──────────────▼──────────────┐   │    │
│  │  │ Deployment: nest-app        │   │    │
│  │  │ - 3 replicas (prod)         │   │    │
│  │  │ - Pod anti-affinity         │   │    │
│  │  │ - 1Gi-2Gi memory limits     │   │    │
│  │  │ - Init containers for deps  │   │    │
│  │  │ - Health checks (liveness)  │   │    │
│  │  └──────────────┬──────────────┘   │    │
│  │                 │                   │    │
│  │    ┌────────────┼────────────┐     │    │
│  │    │            │            │     │    │
│  │  ┌─▼──┐  ┌─────▼────┐  ┌────▼──┐  │    │
│  │  │PG  │  │Redis    │  │Config │  │    │
│  │  │STS │  │Deploy   │  │Maps   │  │    │
│  │  │    │  │         │  │Secrets│  │    │
│  │  └────┘  └─────────┘  └───────┘  │    │
│  │                                   │    │
│  └───────────────────────────────────┘    │
│                                           │
│  (Similar structure for nest-dev and     │
│   nest-staging with environment tweaks)  │
│                                           │
└─────────────────────────────────────────────────┘
```

## Environment Comparison

| Aspect | Dev | Staging | Prod |
|--------|-----|---------|------|
| **App Replicas** | 1 | 2 | 3 |
| **Memory Request** | 256Mi | 512Mi | 1Gi |
| **Memory Limit** | 512Mi | 1Gi | 2Gi |
| **CPU Request** | 250m | 500m | 1000m |
| **CPU Limit** | 500m | 1000m | 2000m |
| **DB Storage** | 10Gi | 20Gi | 50Gi |
| **Cache Storage** | 5Gi | 10Gi | 20Gi |
| **Log Level** | info | warn | error |
| **GIN Mode** | debug | release | release |
| **Pod Anti-Affinity** | No | No | Yes |
| **TLS** | Self-signed | Let's Encrypt (staging) | Let's Encrypt (prod) |
| **Rate Limiting** | No | No | Yes |

## Key Features

### High Availability (Production)

- 3 application replicas with pod anti-affinity
- Automatic pod restarts via liveness probes
- Rolling updates with zero downtime
- Persistent storage for databases

### Security

- Secrets management (ConfigMaps for non-sensitive config)
- Health checks to prevent serving traffic before ready
- Resource limits prevent resource exhaustion
- Network-level isolation via namespaces

### Observability

- Prometheus metrics collection (ServiceMonitor)
- Structured logging with configurable levels
- Health check endpoints
- Pod status and logs accessible via kubectl

### Scalability

- Horizontal Pod Autoscaling support (add HPA manifest)
- StatefulSet for ordered, stable pod identities
- Service discovery via DNS

## Customization

### Update Image Repository

In `40-app-deployment.yaml`, change:
```yaml
image: ghcr.io/penguincloud/core:latest
```

To your registry:
```yaml
image: your-registry.azurecr.io/nest:v1.0.0
```

### Change Domains

In `50-ingress.yaml`, update hostnames:
```yaml
- host: api-dev.example.com
```

To:
```yaml
- host: api-yourcompany.com
```

### Adjust Resource Limits

In deployment manifests, modify:
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Enable External Database

Replace the PostgreSQL StatefulSet with a secret containing:
```yaml
DATABASE_URL: postgresql://user:pass@external-db.example.com/dbname
```

## Deployment Checklist

- [ ] Review and customize all secrets in `11-secrets.yaml`
- [ ] Update domain names in `50-ingress.yaml`
- [ ] Adjust resource limits for your cluster capacity
- [ ] Install cert-manager if using HTTPS
- [ ] Install Prometheus Operator if using monitoring
- [ ] Configure storage classes for PVCs
- [ ] Create backup strategy for PostgreSQL
- [ ] Set up monitoring and alerting
- [ ] Configure RBAC and network policies
- [ ] Test failover and recovery procedures

## Backup Strategy

### PostgreSQL Backup

```bash
# Backup
kubectl exec -it postgres-0 -n nest-prod -- \
  pg_dump -U postgres project_template > backup-$(date +%Y%m%d).sql

# Restore
kubectl exec -i postgres-0 -n nest-prod -- \
  psql -U postgres project_template < backup-20240109.sql
```

### Redis Backup

```bash
# Backup RDB file
kubectl cp nest-prod/redis-xxx:/data/dump.rdb ./redis-backup.rdb

# Restore
kubectl cp ./redis-backup.rdb nest-prod/redis-xxx:/data/dump.rdb
```

## Troubleshooting

### Check Deployment Status

```bash
kubectl get all -n nest-dev -o wide
kubectl describe pod <pod-name> -n nest-dev
kubectl logs <pod-name> -n nest-dev
```

### Database Connection Issues

```bash
# Test from app pod
kubectl exec -it <app-pod> -n nest-dev -- \
  psql -h postgres -U postgres -d project_template

# Check service DNS
kubectl exec -it <app-pod> -n nest-dev -- \
  nslookup postgres
```

### Storage Issues

```bash
kubectl get pvc -n nest-dev
kubectl describe pvc postgres-pvc-0 -n nest-dev
kubectl get storageclass
```

## Production Recommendations

1. **Backup Strategy**
   - Automated daily database backups
   - Cross-region backup replication
   - Regular restore testing

2. **Monitoring**
   - CPU and memory utilization alerts
   - Application error rate monitoring
   - Database connection pool monitoring
   - Disk space warnings

3. **Security**
   - Use external secret management (AWS Secrets Manager, Vault)
   - Implement RBAC and network policies
   - Run pod security policy enforcement
   - Regular security audits and patching

4. **Disaster Recovery**
   - RTO target: 4 hours
   - RPO target: 1 hour
   - Test recovery procedures monthly
   - Document runbooks for common issues

5. **Cost Optimization**
   - Right-size resource requests/limits
   - Use node auto-scaling
   - Implement pod disruption budgets
   - Monitor and optimize storage usage

## Additional Resources

- Full documentation: See `manifests/README.md`
- Deployment script: `manifests/deploy.sh`
- Kubernetes docs: https://kubernetes.io/docs/
- Prometheus Operator: https://prometheus-operator.dev/

## Support

For issues or questions:
1. Check the `manifests/README.md` troubleshooting section
2. Review pod logs and events
3. Consult Kubernetes documentation
4. Contact Penguin Tech support at support@penguintech.io
