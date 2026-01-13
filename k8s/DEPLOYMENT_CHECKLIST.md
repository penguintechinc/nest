# Kubernetes Deployment Checklist for Nest

## Pre-Deployment Requirements

### Infrastructure Setup
- [ ] Kubernetes cluster v1.24+ running and accessible
- [ ] kubectl configured with proper context and credentials
- [ ] Helm v3.0+ installed and verified
- [ ] NGINX ingress controller deployed (for ingress support)
- [ ] cert-manager deployed (for TLS/SSL certificates)
- [ ] Prometheus Operator deployed (for monitoring/metrics)
- [ ] StorageClass configured for persistent volumes

### Database & Cache
- [ ] PostgreSQL database available (or MySQL/MariaDB for Galera)
- [ ] Database user created: `nest_user`
- [ ] Database name created: `nest_prod` (or environment-specific)
- [ ] Redis/Valkey cache available and accessible
- [ ] Database backups configured
- [ ] Connection strings tested and working

### Secrets & Configuration
- [ ] License server URL confirmed: https://license.penguintech.io
- [ ] License API key obtained
- [ ] Database password generated and stored securely
- [ ] Cache password generated and stored securely
- [ ] Flask secret key generated
- [ ] TLS certificates ready or cert-manager configured

### Container Registry
- [ ] Container registry access configured
- [ ] Image pull secrets created (if using private registry)
- [ ] Nest application image built and pushed
- [ ] Image versions tagged appropriately

## Pre-Deployment Validation

### 1. Helm Chart Validation
```bash
# Lint the Helm chart
helm lint ./k8s/helm/nest

# Dry-run installation
helm install nest ./k8s/helm/nest \
  --dry-run --debug \
  -f ./k8s/helm/nest/values-prod.yaml

# Validate rendered templates
helm template nest ./k8s/helm/nest \
  -f ./k8s/helm/nest/values-prod.yaml > /tmp/rendered.yaml
```

### 2. Kubernetes Cluster Validation
```bash
# Check cluster version
kubectl version --short

# Check node status
kubectl get nodes

# Verify ingress controller
kubectl get ingress -A

# Verify cert-manager
kubectl get clusterissuers

# Verify storage classes
kubectl get storageclass
```

### 3. Database Connectivity
```bash
# Test PostgreSQL connection
psql -h <host> -U nest_user -d nest_prod -c "SELECT 1"

# Test Redis/Valkey connection
redis-cli -h <host> ping
```

## Deployment Steps

### Step 1: Create Namespace
```bash
kubectl create namespace nest-prod
```

### Step 2: Create Secret for Credentials
```bash
kubectl create secret generic nest-credentials \
  --from-literal=database-password='<your-db-password>' \
  --from-literal=cache-password='<your-cache-password>' \
  --from-literal=license-api-key='<your-license-key>' \
  --from-literal=app-secret-key='<your-secret-key>' \
  -n nest-prod
```

Or use sealed-secrets:
```bash
# Create a sealed secret
cat > secret.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: nest-credentials
  namespace: nest-prod
type: Opaque
stringData:
  database-password: <your-db-password>
  cache-password: <your-cache-password>
  license-api-key: <your-license-key>
  app-secret-key: <your-secret-key>
