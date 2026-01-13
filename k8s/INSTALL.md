# Quick Start: Deploying Nest on Kubernetes

## Prerequisites Checklist

- [ ] Kubernetes cluster running (v1.24+)
- [ ] `kubectl` configured for your cluster
- [ ] `helm` v3.0+ installed
- [ ] NGINX Ingress Controller installed (for production)
- [ ] cert-manager installed (for TLS)

## Quick Installation

### 1. Create Namespace

```bash
kubectl create namespace nest-prod
```

### 2. Deploy with Helm

For **Production**:
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -n nest-prod
```

For **Staging**:
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-staging.yaml \
  -n nest-staging \
  --create-namespace
```

For **Development**:
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-dev.yaml \
  -n nest-dev \
  --create-namespace
```

### 3. Verify Deployment

```bash
# Wait for pods to be ready
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=nest \
  -n nest-prod \
  --timeout=300s

# Check status
kubectl get all -n nest-prod
```

### 4. Access the Application

```bash
# Get the Ingress IP/hostname
kubectl get ingress -n nest-prod

# For development/local testing
kubectl port-forward svc/nest 8000:8000 -n nest-prod
# Then access: http://localhost:8000
```

## Configuration

### Set Database Credentials

Create a custom values file with your database connection:

```yaml
# my-values.yaml
database:
  externalConnection:
    host: your-postgres.example.com
    port: 5432
    database: nest_prod
    username: nest_user

cache:
  externalConnection:
    host: your-redis.example.com
    port: 6379
```

Then deploy with:
```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -f ./my-values.yaml \
  -n nest-prod
```

### Set Secrets

For sensitive data, use Kubernetes secrets:

```bash
kubectl create secret generic nest-prod-secrets \
  --from-literal=database-password='your-password' \
  --from-literal=cache-password='your-cache-password' \
  --from-literal=license-api-key='your-license-key' \
  --from-literal=app-secret-key='your-secret-key' \
  -n nest-prod
```

Or use the Helm `--set` flag:

```bash
helm install nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  --set 'secrets.database.password=your-password' \
  --set 'secrets.cache.password=your-cache-password' \
  --set 'secrets.license.apiKey=your-license-key' \
  --set 'secrets.app.secretKey=your-secret-key' \
  -n nest-prod
```

## Common Tasks

### View Logs

```bash
# Real-time logs
kubectl logs -f -n nest-prod -l app.kubernetes.io/name=nest

# Last 100 lines
kubectl logs -n nest-prod -l app.kubernetes.io/name=nest --tail=100
```

### Scale Replicas

```bash
# Manual scaling
kubectl scale deployment nest -n nest-prod --replicas=5

# Edit HPA
kubectl edit hpa nest -n nest-prod
```

### Update Image

```bash
# Update image tag
kubectl set image deployment/nest \
  nest=penguintech/nest:v1.1.0 \
  -n nest-prod

# Monitor rollout
kubectl rollout status deployment/nest -n nest-prod
```

### Access Database

```bash
# Port forward to database
kubectl port-forward -n nest-prod \
  svc/postgres 5432:5432 &

# Connect
psql -h localhost -U nest_user -d nest_prod
```

### Check Metrics

```bash
# View Prometheus targets
kubectl port-forward -n prometheus svc/prometheus 9090:9090 &
# Then visit: http://localhost:9090/targets
```

## Troubleshooting

### Pod stuck in Pending

```bash
# Check resource availability
kubectl describe node

# Check pod events
kubectl describe pod -n nest-prod <pod-name>
```

### CrashLoopBackOff

```bash
# Check logs
kubectl logs -n nest-prod <pod-name>

# Check previous logs
kubectl logs -n nest-prod <pod-name> --previous
```

### Connection to Database Failed

```bash
# Verify ConfigMap
kubectl get configmap -n nest-prod nest-config -o yaml

# Test connectivity
kubectl run -it --rm debug \
  --image=postgres:16 \
  --restart=Never \
  -- psql -h <host> -U <user> -d <database>
```

## Updating the Deployment

```bash
# Update Helm values
helm upgrade nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml \
  -n nest-prod

# Check rollout status
kubectl rollout status deployment/nest -n nest-prod

# Rollback if needed
helm rollback nest -n nest-prod
```

## Cleaning Up

```bash
# Delete the release
helm uninstall nest -n nest-prod

# Delete the namespace
kubectl delete namespace nest-prod
```

## Next Steps

1. Configure database connection in values files
2. Set up external secrets management (sealed-secrets or external-secrets-operator)
3. Configure TLS certificates with cert-manager
4. Deploy Prometheus and Grafana for monitoring
5. Set up ingress domain configuration
6. Enable network policies for production
7. Configure pod security policies

For detailed documentation, see [README.md](./README.md)
