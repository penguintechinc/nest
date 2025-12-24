# Database Templates - Configuration Examples

This document provides practical examples for configuring and deploying database StatefulSets using the Nest templates.

## Quick Start Examples

### Minimal PostgreSQL Deployment

```yaml
# values-postgresql-minimal.yaml
namespace: default
storage_class: standard

postgresql_name: postgresql
postgresql_replicas: 1
postgresql_database: myapp
postgresql_user: appuser
postgresql_password: changeme123
postgresql_root_password: rootpass123
```

Apply with Helm:
```bash
helm template postgresql ./templates \
  -f values-postgresql-minimal.yaml | kubectl apply -f -
```

### Development Environment Setup

```yaml
# values-dev.yaml
namespace: development
storage_class: standard

# PostgreSQL
postgresql_name: postgres-dev
postgresql_replicas: 1
postgresql_storage_size: 5Gi
postgresql_database: dev_db
postgresql_user: dev_user
postgresql_password: dev_password123
postgresql_memory_request: 128Mi
postgresql_memory_limit: 256Mi
postgresql_cpu_request: 50m
postgresql_cpu_limit: 100m

# Redis
redis_name: redis-dev
redis_replicas: 1
redis_storage_size: 1Gi
redis_password_enabled: false
redis_memory_request: 64Mi
redis_memory_limit: 128Mi

# MariaDB (optional)
mariadb_name: mariadb-dev
mariadb_replicas: 1
mariadb_storage_size: 5Gi
mariadb_database: dev_db
mariadb_user: dev_user
mariadb_password: dev_password123
mariadb_root_password: dev_root123
```

Deploy:
```bash
kubectl create namespace development
helm template nest ./templates -f values-dev.yaml | kubectl apply -f -
```

### Production High-Availability Setup

```yaml
# values-production-ha.yaml
namespace: production
storage_class: fast-ssd

# PostgreSQL HA Cluster
postgresql_name: postgresql-prod
postgresql_replicas: 3
postgresql_storage_size: 500Gi
postgresql_wal_storage_size: 100Gi
postgresql_database: production_db
postgresql_user: prod_user
postgresql_password: $(openssl rand -base64 32)
postgresql_root_password: $(openssl rand -base64 32)
postgresql_memory_request: 1Gi
postgresql_memory_limit: 2Gi
postgresql_cpu_request: 500m
postgresql_cpu_limit: 2
postgresql_sslmode: require

# Redis HA with Authentication
redis_name: redis-prod
redis_replicas: 3
redis_storage_size: 50Gi
redis_password_enabled: true
redis_password: $(openssl rand -base64 32)
redis_memory_request: 512Mi
redis_memory_limit: 1Gi
redis_cpu_request: 200m
redis_cpu_limit: 1

# MariaDB Production
mariadb_name: mariadb-prod
mariadb_replicas: 1
mariadb_storage_size: 500Gi
mariadb_database: production_db
mariadb_user: prod_user
mariadb_password: $(openssl rand -base64 32)
mariadb_root_password: $(openssl rand -base64 32)
mariadb_memory_request: 2Gi
mariadb_memory_limit: 4Gi
mariadb_cpu_request: 1
mariadb_cpu_limit: 2
```

### Secure Valkey with TLS

```yaml
# values-valkey-tls.yaml
namespace: production

valkey_name: valkey-secure
valkey_replicas: 1
valkey_storage_size: 20Gi
valkey_password_enabled: true
valkey_password: secure-password-here
valkey_tls_enabled: true
valkey_memory_limit: 1Gi
valkey_cpu_limit: 1

# TLS certificates (base64 encoded)
# Generate with: cat file | base64 -w0
valkey_tls_cert: |
  LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUN...truncated...
valkey_tls_key: |
  LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JSUU...truncated...
valkey_ca_cert: |
  LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCk1JSUN...truncated...
```

## Database Initialization

### PostgreSQL Initialization Script

Create a ConfigMap with initialization SQL:

```bash
cat > init-postgres.sql << 'EOF'
-- Create extensions
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create application schema
CREATE SCHEMA IF NOT EXISTS app_schema;

-- Create tables
CREATE TABLE app_schema.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON app_schema.users(email);
EOF

kubectl create configmap postgresql-init-scripts \
  --from-file=init-postgres.sql \
  --namespace=default
```

Update template variable:
```yaml
postgresql_init_scripts_config: postgresql-init-scripts
```

### MariaDB Initialization

```bash
cat > init-mariadb.sql << 'EOF'
-- Create database
CREATE DATABASE IF NOT EXISTS app_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Create user with specific privileges
CREATE USER IF NOT EXISTS 'app_user'@'%' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON app_db.* TO 'app_user'@'%';

-- Create tables
USE app_db;
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

FLUSH PRIVILEGES;
EOF

kubectl create configmap mariadb-init-scripts \
  --from-file=init-mariadb.sql \
  --namespace=default
```

## TLS Certificate Generation

### Generate Self-Signed Certificates

```bash
#!/bin/bash
# generate-tls-certs.sh

DAYS=365
BITS=2048

# Generate CA private key
openssl genrsa -out ca.key ${BITS}

# Generate CA certificate
openssl req -new -x509 -days ${DAYS} -key ca.key -out ca.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=database-ca"

# Generate server private key
openssl genrsa -out tls.key ${BITS}

# Generate server certificate signing request
openssl req -new -key tls.key -out server.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=postgresql.default.svc.cluster.local"

# Sign server certificate with CA
openssl x509 -req -days ${DAYS} -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial -out tls.crt

# Convert to base64 for Kubernetes secrets
echo "TLS Certificate (base64):"
cat tls.crt | base64 -w0 | tee tls.crt.b64

echo -e "\nTLS Key (base64):"
cat tls.key | base64 -w0 | tee tls.key.b64

echo -e "\nCA Certificate (base64):"
cat ca.crt | base64 -w0 | tee ca.crt.b64
```

Run the script:
```bash
bash generate-tls-certs.sh
```

Create Kubernetes secret:
```bash
kubectl create secret tls database-tls \
  --cert=tls.crt \
  --key=tls.key \
  --namespace=default
```

## Helm Values File Structure

Complete `values.yaml` for all services:

```yaml
# Global configuration
namespace: default
storage_class: standard
application_name: nest-app

# PostgreSQL Configuration
postgresql:
  enabled: true
  name: postgresql
  replicas: 1
  image: postgres:16-alpine
  storage_size: 10Gi
  wal_storage_size: 5Gi
  database: myapp
  user: appuser
  password: changeme
  root_password: rootchangeme
  memory_request: 256Mi
  memory_limit: 512Mi
  cpu_request: 100m
  cpu_limit: 500m
  secret_name: postgresql-secret
  sslmode: prefer

# Redis Configuration
redis:
  enabled: true
  name: redis
  replicas: 1
  image: redis:7-alpine
  storage_size: 5Gi
  password_enabled: false
  password: ""
  memory_request: 128Mi
  memory_limit: 256Mi
  cpu_request: 50m
  cpu_limit: 200m
  secret_name: redis-secret
  protocol: redis

# MariaDB Configuration
mariadb:
  enabled: false
  name: mariadb
  replicas: 1
  image: mariadb:11-jammy
  storage_size: 10Gi
  database: myapp
  user: appuser
  password: changeme
  root_password: rootchangeme
  charset: utf8mb4
  collation: utf8mb4_unicode_ci
  memory_request: 256Mi
  memory_limit: 512Mi
  cpu_request: 100m
  cpu_limit: 500m
  secret_name: mariadb-secret

# Valkey Configuration
valkey:
  enabled: false
  name: valkey
  replicas: 1
  image: valkey/valkey:7-alpine
  storage_size: 5Gi
  password_enabled: false
  password: ""
  tls_enabled: false
  memory_request: 128Mi
  memory_limit: 256Mi
  cpu_request: 50m
  cpu_limit: 200m
  secret_name: valkey-secret
  protocol: valkey

# TLS Configuration
tls:
  enabled: false
  secret_name: database-tls
  ca_secret_name: database-ca
  mtls_secret_name: database-mtls-client
```

## Deployment Scripts

### Deploy All Services

```bash
#!/bin/bash
# deploy-databases.sh

set -e

NAMESPACE=${1:-default}
VALUES_FILE=${2:-values.yaml}

echo "Deploying databases to namespace: ${NAMESPACE}"

# Create namespace if it doesn't exist
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
echo "Creating secrets..."
helm template nest ./templates -f ${VALUES_FILE} \
  --include-crds | grep -A 100 "^---$" | grep "kind: Secret" | \
  helm template nest ./templates -f ${VALUES_FILE} | \
  grep "kind: Secret" -A 100 | kubectl apply -n ${NAMESPACE} -f -

# Deploy StatefulSets
echo "Deploying StatefulSets..."
helm template nest ./templates -f ${VALUES_FILE} | \
  grep "kind: StatefulSet" -A 100 | kubectl apply -n ${NAMESPACE} -f -

echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod \
  -l managed-by=nest \
  -n ${NAMESPACE} \
  --timeout=300s

echo "Database deployment complete!"
kubectl get statefulset -n ${NAMESPACE}
```

Usage:
```bash
bash deploy-databases.sh production values-production-ha.yaml
```

### Cleanup Script

```bash
#!/bin/bash
# cleanup-databases.sh

set -e

NAMESPACE=${1:-default}

echo "Removing database deployments from namespace: ${NAMESPACE}"

# Delete StatefulSets (will keep PVCs)
kubectl delete statefulset -l managed-by=nest -n ${NAMESPACE}

# Delete Services
kubectl delete svc -l managed-by=nest -n ${NAMESPACE}

# Delete Secrets
kubectl delete secret -l managed-by=nest -n ${NAMESPACE}

# Option to delete PVCs
read -p "Delete persistent volumes? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  kubectl delete pvc -l managed-by=nest -n ${NAMESPACE}
fi

echo "Cleanup complete!"
```

## Monitoring and Health Checks

### Port-Forward for Local Testing

```bash
# PostgreSQL
kubectl port-forward svc/postgresql-headless 5432:5432 -n default

# Redis
kubectl port-forward svc/redis-headless 6379:6379 -n default

# Test connection
psql -h localhost -U appuser -d myapp
redis-cli -h localhost
```

### Monitor Pod Status

```bash
# Watch pods
kubectl get pods -l managed-by=nest -w

# Check StatefulSet rollout status
kubectl rollout status statefulset/postgresql -n default

# View events
kubectl describe statefulset postgresql -n default
kubectl get events -n default --sort-by='.lastTimestamp'
```

### Database-Specific Health Commands

```bash
# PostgreSQL health check
kubectl exec -it postgresql-0 -- \
  pg_isready -U appuser -d myapp

# Redis health check
kubectl exec -it redis-0 -- \
  redis-cli ping

# MariaDB health check
kubectl exec -it mariadb-0 -- \
  mysqladmin ping -u root -p${MARIADB_ROOT_PASSWORD}

# Valkey health check
kubectl exec -it valkey-0 -- \
  valkey-cli ping
```

## Backup and Recovery

### PostgreSQL Backup

```bash
# Create backup
kubectl exec -it postgresql-0 -- \
  pg_dump -U appuser -d myapp > backup.sql

# Restore backup
kubectl exec -i postgresql-0 -- \
  psql -U appuser -d myapp < backup.sql
```

### Redis Backup

```bash
# Create RDB snapshot
kubectl exec -it redis-0 -- \
  redis-cli BGSAVE

# Copy backup to local
kubectl cp redis-0:/data/dump.rdb ./redis-backup.rdb
```

### MariaDB Backup

```bash
# Create backup
kubectl exec -it mariadb-0 -- \
  mysqldump -u root -p${MARIADB_ROOT_PASSWORD} \
  --all-databases > backup.sql

# Restore backup
kubectl exec -i mariadb-0 -- \
  mysql -u root -p${MARIADB_ROOT_PASSWORD} < backup.sql
```

## Environment-Specific Configurations

### Staging Configuration

```yaml
# values-staging.yaml
namespace: staging
storage_class: standard

postgresql_replicas: 2
postgresql_storage_size: 50Gi
redis_replicas: 2
redis_storage_size: 10Gi
```

### QA Configuration

```yaml
# values-qa.yaml
namespace: qa
storage_class: standard

postgresql_replicas: 1
postgresql_storage_size: 10Gi
redis_password_enabled: true
mariadb_enabled: true
```

### CI/CD Integration

```bash
#!/bin/bash
# ci-deploy.sh - For GitHub Actions/GitLab CI

if [ "${CI_ENVIRONMENT_NAME}" = "production" ]; then
  VALUES_FILE="values-production-ha.yaml"
  NAMESPACE="production"
elif [ "${CI_ENVIRONMENT_NAME}" = "staging" ]; then
  VALUES_FILE="values-staging.yaml"
  NAMESPACE="staging"
else
  VALUES_FILE="values-dev.yaml"
  NAMESPACE="development"
fi

helm template nest ./templates -f ${VALUES_FILE} | \
  kubectl apply -n ${NAMESPACE} -f -
```

## Troubleshooting Examples

### Pod Stuck in Pending

```bash
# Check resource availability
kubectl describe pod postgresql-0

# Check storage class
kubectl get storageclass
kubectl describe storageclass standard

# Check PVC status
kubectl get pvc
kubectl describe pvc postgresql-storage-postgresql-0
```

### Connection Issues

```bash
# Test DNS resolution
kubectl exec -it postgresql-0 -- \
  nslookup postgresql-headless.default.svc.cluster.local

# Check service endpoints
kubectl get endpoints postgresql-headless

# Verify network policies
kubectl get networkpolicies
```

### Performance Tuning

```yaml
# values-performance.yaml
postgresql_memory_limit: 4Gi
postgresql_cpu_limit: 4
redis_memory_limit: 2Gi
redis_cpu_limit: 2
storage_class: fast-ssd
```

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Commands](https://redis.io/commands)
- [MariaDB Documentation](https://mariadb.com/docs/)
- [Valkey Documentation](https://valkey.io/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
