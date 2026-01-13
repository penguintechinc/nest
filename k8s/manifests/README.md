# Nest Kubernetes Manifests

Direct kubectl deployment manifests for Nest application across development, staging, and production environments.

## Directory Structure

```
manifests/
├── 00-namespace.yaml           # Namespace definitions (nest-dev, nest-staging, nest-prod)
├── 10-configmap.yaml           # Application configuration for all environments
├── 11-secrets.yaml             # Secrets template with placeholders
├── 20-postgres-statefulset.yaml # PostgreSQL database with persistent storage
├── 21-postgres-service.yaml    # PostgreSQL service
├── 30-redis-deployment.yaml    # Redis/Valkey cache deployment
├── 31-redis-service.yaml       # Redis service
├── 40-app-deployment.yaml      # Main Nest application deployment
├── 41-app-service.yaml         # Application service
├── 50-ingress.yaml             # Ingress with TLS support
├── 60-servicemonitor.yaml      # Prometheus ServiceMonitor for metrics
└── README.md                   # This file
```

## Prerequisites

- Kubernetes 1.19+
- kubectl CLI configured with cluster access
- Persistent storage provisioner (for database and cache volumes)
- Ingress controller (nginx recommended)
- cert-manager (for TLS certificates)
- Prometheus Operator (optional, for ServiceMonitor)

## Quick Start

### 1. Create Namespaces

```bash
kubectl apply -f manifests/00-namespace.yaml
```

### 2. Configure Secrets

Edit `manifests/11-secrets.yaml` with your actual values:

```bash
# Development example
POSTGRES_PASSWORD: "your_dev_postgres_password"
REDIS_PASSWORD: "your_dev_redis_password"
LICENSE_KEY: "PENG-XXXX-XXXX-XXXX-XXXX-ABCD"
JWT_SECRET: "your_dev_jwt_secret"
SESSION_SECRET: "your_dev_session_secret"
```

Then apply:

```bash
kubectl apply -f manifests/10-configmap.yaml
kubectl apply -f manifests/11-secrets.yaml
```

### 3. Deploy Infrastructure

Deploy PostgreSQL and Redis:

```bash
kubectl apply -f manifests/20-postgres-statefulset.yaml
kubectl apply -f manifests/21-postgres-service.yaml
kubectl apply -f manifests/30-redis-deployment.yaml
kubectl apply -f manifests/31-redis-service.yaml
```

### 4. Deploy Application

```bash
kubectl apply -f manifests/40-app-deployment.yaml
kubectl apply -f manifests/41-app-service.yaml
```

### 5. Setup Ingress (with TLS)

Before applying ingress, ensure cert-manager is installed:

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

Then apply ingress:

```bash
# Update domains in 50-ingress.yaml first
kubectl apply -f manifests/50-ingress.yaml
```

### 6. Setup Monitoring (Optional)

Install Prometheus Operator:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack
```

Then apply ServiceMonitor:

```bash
kubectl apply -f manifests/60-servicemonitor.yaml
```

## Complete Deployment Script

```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-nest-dev}

echo "Deploying Nest to $ENVIRONMENT..."

# Apply all manifests in order
kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/10-configmap.yaml
kubectl apply -f manifests/11-secrets.yaml
kubectl apply -f manifests/20-postgres-statefulset.yaml
kubectl apply -f manifests/21-postgres-service.yaml
kubectl apply -f manifests/30-redis-deployment.yaml
kubectl apply -f manifests/31-redis-service.yaml
kubectl apply -f manifests/40-app-deployment.yaml
kubectl apply -f manifests/41-app-service.yaml
kubectl apply -f manifests/50-ingress.yaml
kubectl apply -f manifests/60-servicemonitor.yaml

echo "Deployment complete!"

# Wait for rollout
kubectl rollout status deployment/nest-app -n $ENVIRONMENT --timeout=5m
```

## Configuration

### Environment-Specific Settings

All manifests contain configurations for three environments:

**Development (nest-dev):**
- 1 app replica
- 256Mi memory request, 512Mi limit
- Debug logging enabled
- SSL/TLS disabled

**Staging (nest-staging):**
- 2 app replicas
- 512Mi memory request, 1Gi limit
- Warning level logging
- SSL/TLS enabled

**Production (nest-prod):**
- 3 app replicas with pod anti-affinity
- 1Gi memory request, 2Gi limit
- Error level logging
- SSL/TLS required, rate limiting enabled

### Updating ConfigMap

```bash
kubectl set env configmap/nest-config LOG_LEVEL=debug -n nest-dev
```

### Updating Secrets

```bash
kubectl create secret generic nest-secrets \
  --from-literal=POSTGRES_PASSWORD=newpassword \
  --dry-run=client -o yaml | kubectl apply -f - -n nest-dev
```

## Volume Management

### PostgreSQL Storage

- **Development:** 10Gi
- **Staging:** 20Gi
- **Production:** 50Gi

Resize a PVC:

```bash
kubectl patch pvc postgres-pvc -p '{"spec":{"resources":{"requests":{"storage":"15Gi"}}}}' -n nest-dev
```

### Redis Storage

- **Development:** 5Gi
- **Staging:** 10Gi
- **Production:** 20Gi

## Monitoring & Debugging

### View Logs

```bash
# Application logs
kubectl logs -f deployment/nest-app -n nest-dev

# PostgreSQL logs
kubectl logs -f statefulset/postgres -n nest-dev

# Redis logs
kubectl logs -f deployment/redis -n nest-dev
```

### Pod Status

```bash
kubectl get pods -n nest-dev -o wide
kubectl describe pod <pod-name> -n nest-dev
```

### Port Forwarding

```bash
# Access app locally
kubectl port-forward svc/nest-app 8080:8080 -n nest-dev

# Access PostgreSQL
kubectl port-forward svc/postgres 5432:5432 -n nest-dev

# Access Redis
kubectl port-forward svc/redis 6379:6379 -n nest-dev
```

### Check Ingress

```bash
kubectl get ingress -n nest-dev
kubectl describe ingress nest-ingress -n nest-dev
```

## Resource Quotas & Limits

Set resource quotas per namespace:

```bash
kubectl create quota nest-quota \
  --hard=requests.cpu=5,requests.memory=10Gi,limits.cpu=10,limits.memory=20Gi \
  -n nest-dev
```

## Scaling

Scale deployments:

```bash
kubectl scale deployment nest-app --replicas=5 -n nest-prod
```

## Cleanup

Remove all Nest resources:

```bash
# Delete specific namespace (removes all resources within)
kubectl delete namespace nest-dev

# Or delete individual resources
kubectl delete -f manifests/ -n nest-dev
```

## Common Issues

### Pod stuck in Pending

```bash
kubectl describe pod <pod-name> -n <namespace>
# Check PVC status and storage availability
kubectl get pvc -n nest-dev
```

### Database connection failures

```bash
# Check database service
kubectl get service postgres -n nest-dev

# Test connectivity from app pod
kubectl exec -it <app-pod> -n nest-dev -- nc -zv postgres 5432
```

### Certificate issues with Ingress

```bash
# Check certificate status
kubectl get certificate -n nest-dev

# View cert-manager logs
kubectl logs -f -n cert-manager deployment/cert-manager
```

### Redis authentication errors

```bash
# Verify Redis secret is correct
kubectl get secret nest-secrets -n nest-dev -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d

# Test Redis connectivity
kubectl exec -it <app-pod> -n nest-dev -- redis-cli -h redis -a $(kubectl get secret nest-secrets -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d) ping
```

## Backup & Recovery

### Backup PostgreSQL

```bash
kubectl exec -it <postgres-pod> -n nest-dev -- pg_dump -U postgres project_template > backup.sql
```

### Restore PostgreSQL

```bash
kubectl exec -i <postgres-pod> -n nest-dev -- psql -U postgres project_template < backup.sql
```

## Security Best Practices

1. **Secrets Management:**
   - Use external secret management (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
   - Never commit secrets to version control
   - Rotate credentials regularly

2. **Network Policies:**
   - Implement network policies to restrict traffic
   - Use service mesh for advanced networking

3. **RBAC:**
   - Create service accounts per deployment
   - Apply principle of least privilege

4. **Pod Security:**
   - Run containers as non-root users
   - Use read-only root filesystems where possible
   - Enable security contexts and pod security policies

Example NetworkPolicy:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: nest-network-policy
  namespace: nest-prod
spec:
  podSelector:
    matchLabels:
      app: nest
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nest
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: nest
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

## Advanced Topics

### Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nest-hpa
  namespace: nest-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nest-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Pod Disruption Budgets

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nest-pdb
  namespace: nest-prod
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: nest
      component: application
```

## Helm Chart Alternative

These manifests provide kubectl-only deployment. For Helm-based deployment, refer to the helm/ directory.

## Support & Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Prometheus ServiceMonitor Documentation](https://prometheus-operator.dev/docs/operator/latest/api/#monitoring.coreos.com/v1.ServiceMonitor)
