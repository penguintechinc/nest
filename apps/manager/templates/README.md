# Kubernetes Database Templates for Nest Manager

This directory contains Jinja2 templated Kubernetes manifests for provisioning and managing database services in the Nest application.

## Directory Structure

```
templates/
├── statefulset/
│   ├── postgresql.yaml     - PostgreSQL StatefulSet with persistent storage
│   ├── redis.yaml          - Redis in-memory cache with AOF persistence
│   ├── mariadb.yaml        - MariaDB SQL database StatefulSet
│   └── valkey.yaml         - Valkey cache (Redis alternative) with TLS support
├── secrets/
│   ├── postgresql-secret.yaml  - PostgreSQL credentials and connection strings
│   ├── redis-secret.yaml       - Redis authentication and connection strings
│   ├── mariadb-secret.yaml     - MariaDB credentials and connection strings
│   ├── valkey-secret.yaml      - Valkey credentials and TLS configuration
│   └── tls-secret.yaml         - TLS certificates for encrypted connections
├── deployments/
│   └── (placeholder for application deployments)
└── README.md               - This file
```

## StatefulSet Templates

### PostgreSQL (postgresql.yaml)

**Purpose**: Relational database for structured data storage with ACID compliance

**Key Features**:
- Image: `postgres:16-alpine` (lightweight, secure)
- Default port: 5432
- Persistent volumes: 10Gi data + 5Gi WAL storage
- Replication support (configurable replicas)
- Health checks: Liveness and readiness probes
- Security context: Non-root user (UID 999)
- Pod anti-affinity for HA deployment

**Jinja2 Variables**:
```yaml
postgresql_name: 'postgresql'
postgresql_replicas: 1
postgresql_image: 'postgres:16-alpine'
postgresql_storage_size: '10Gi'
postgresql_wal_storage_size: '5Gi'
postgresql_database: 'postgres'
postgresql_user: 'postgres'
postgresql_password: ''
postgresql_root_password: ''
postgresql_memory_request: '256Mi'
postgresql_memory_limit: '512Mi'
postgresql_cpu_request: '100m'
postgresql_cpu_limit: '500m'
postgresql_secret_name: 'postgresql-secret'
postgresql_init_scripts_config: 'postgresql-init-scripts'
postgresql_sslmode: 'prefer'
storage_class: 'standard'
namespace: 'default'
```

**Service**:
- Headless service for stable network identity
- Service name: `{{ postgresql_name }}-headless`

### Redis (redis.yaml)

**Purpose**: High-performance in-memory data structure store with persistence

**Key Features**:
- Image: `redis:7-alpine`
- Default port: 6379
- AOF (Append-Only File) persistence enabled
- Configurable password protection
- Persistent volume: 5Gi
- Metrics endpoint: Port 9187 (Prometheus)
- Health checks via `redis-cli` commands

**Jinja2 Variables**:
```yaml
redis_name: 'redis'
redis_replicas: 1
redis_image: 'redis:7-alpine'
redis_storage_size: '5Gi'
redis_password_enabled: false
redis_password: ''
redis_memory_request: '128Mi'
redis_memory_limit: '256Mi'
redis_cpu_request: '50m'
redis_cpu_limit: '200m'
redis_secret_name: 'redis-secret'
redis_protocol: 'redis'
storage_class: 'standard'
namespace: 'default'
```

**Service**:
- Headless service for StatefulSet
- Service name: `{{ redis_name }}-headless`

### MariaDB (mariadb.yaml)

**Purpose**: MySQL-compatible relational database with advanced features

**Key Features**:
- Image: `mariadb:11-jammy`
- Default port: 3306
- Persistent volume: 10Gi
- Support for custom initialization scripts
- Configurable character set and collation (default: utf8mb4)
- Health checks via `mysqladmin ping`
- Security context: Non-root user

**Jinja2 Variables**:
```yaml
mariadb_name: 'mariadb'
mariadb_replicas: 1
mariadb_image: 'mariadb:11-jammy'
mariadb_storage_size: '10Gi'
mariadb_database: 'mariadb'
mariadb_user: 'mariadb'
mariadb_password: ''
mariadb_root_password: ''
mariadb_charset: 'utf8mb4'
mariadb_collation: 'utf8mb4_unicode_ci'
mariadb_memory_request: '256Mi'
mariadb_memory_limit: '512Mi'
mariadb_cpu_request: '100m'
mariadb_cpu_limit: '500m'
mariadb_secret_name: 'mariadb-secret'
mariadb_config_name: 'mariadb-config'
mariadb_init_scripts_config: 'mariadb-init-scripts'
storage_class: 'standard'
namespace: 'default'
```

**Service**:
- Headless service for stable network identity
- Service name: `{{ mariadb_name }}-headless`

### Valkey (valkey.yaml)

**Purpose**: Modern Redis alternative with improved performance and additional features

**Key Features**:
- Image: `valkey/valkey:7-alpine`
- Default port: 6379
- Optional TLS support (port 6380)
- AOF and RDB persistence
- Optional password protection
- Persistent volume: 5Gi
- Pod anti-affinity for distribution

**Jinja2 Variables**:
```yaml
valkey_name: 'valkey'
valkey_replicas: 1
valkey_image: 'valkey/valkey:7-alpine'
valkey_storage_size: '5Gi'
valkey_password_enabled: false
valkey_password: ''
valkey_tls_enabled: false
valkey_tls_cert: 'base64-encoded-cert'
valkey_tls_key: 'base64-encoded-key'
valkey_ca_cert: 'base64-encoded-ca'
valkey_memory_request: '128Mi'
valkey_memory_limit: '256Mi'
valkey_cpu_request: '50m'
valkey_cpu_limit: '200m'
valkey_secret_name: 'valkey-secret'
valkey_tls_secret_name: 'valkey-tls'
valkey_protocol: 'valkey'
storage_class: 'standard'
namespace: 'default'
```

**Service**:
- Headless service for StatefulSet
- Supports both standard and TLS connections
- Service name: `{{ valkey_name }}-headless`

## Secret Templates

### PostgreSQL Secret (postgresql-secret.yaml)

Contains PostgreSQL connection credentials and configuration:
- `database-name`: Target database name
- `username`: Database user
- `password`: User password
- `root-password`: Root/superuser password
- `database-url`: Full connection string (postgresql://user:pass@host:5432/db)
- Connection parameters: `host`, `port`, `db`
- `sslmode`: TLS configuration (prefer, require, disable)

### Redis Secret (redis-secret.yaml)

Contains Redis connection credentials:
- `password`: Optional authentication password
- `redis-url`: Connection URI without auth
- `redis-url-with-auth`: Connection URI with password (if enabled)
- Connection parameters: `host`, `port`, `database`
- `auth-enabled`: Boolean flag for password protection
- `aof-enabled`: AOF persistence status

### MariaDB Secret (mariadb-secret.yaml)

Contains MariaDB connection credentials:
- `database-name`: Target database name
- `username`: Database user
- `password`: User password
- `root-password`: Root password
- `database-url`: Full connection string (mysql://user:pass@host:3306/db)
- Connection parameters: `host`, `port`, `db`
- `charset`: Character set configuration
- `collation`: Collation configuration

### Valkey Secret (valkey-secret.yaml)

Contains Valkey connection credentials and TLS configuration:
- `password`: Optional authentication password
- `valkey-url`: Standard connection URI
- `valkey-url-with-auth`: URI with password (if enabled)
- `valkey-url-tls`: TLS connection URI (if enabled)
- Connection parameters: `host`, `port`, `database`, `tls-port`
- `auth-enabled`: Password protection status
- `tls-enabled`: TLS/encryption status
- Optional: Embedded TLS secrets for mTLS

### TLS Secret (tls-secret.yaml)

Manages TLS certificates for encrypted database connections:
- Database TLS certificates (`database-tls` secret)
  - `tls.crt`: Server certificate
  - `tls.key`: Server private key
- CA certificates (`database-ca` secret)
  - `ca.crt`: Certificate Authority certificate
  - `ca.key`: CA private key (optional)
- mTLS client certificates (`database-mtls-client` secret)
  - `tls.crt`: Client certificate
  - `tls.key`: Client private key

**Certificate Generation**:
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout tls.key -out tls.crt -days 365 -nodes

# Encode for Kubernetes secret (base64 -w0 removes line wrapping)
cat tls.crt | base64 -w0
cat tls.key | base64 -w0
```

## Deployment Usage

### 1. Install with Helm (Recommended)

Create a `values.yaml` for your deployment:
```yaml
namespace: production
storage_class: fast-ssd

postgresql:
  enabled: true
  name: postgres-prod
  replicas: 1
  storage_size: 50Gi
  database: app_db
  user: app_user
  password: changeme

redis:
  enabled: true
  name: redis-prod
  replicas: 1
  storage_size: 10Gi
  password_enabled: true
  password: changeme
```

Apply templates with Helm:
```bash
helm template nest ./templates -f values.yaml | kubectl apply -f -
```

### 2. Apply with Jinja2 Template Engine

```bash
# Using j2cli
j2 -f yaml statefulset/postgresql.yaml vars.yaml | kubectl apply -f -

# Using Python Jinja2
python3 << 'EOF'
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('statefulset/postgresql.yaml')
output = template.render(
    namespace='default',
    postgresql_name='postgres',
    postgresql_database='myapp'
)
EOF
```

### 3. Manual kubectl apply

```bash
# Deploy secrets first
kubectl apply -f secrets/postgresql-secret.yaml

# Deploy StatefulSet
kubectl apply -f statefulset/postgresql.yaml

# Verify deployment
kubectl get statefulset
kubectl get pods
kubectl describe statefulset postgresql
```

## Configuration Examples

### High-Availability PostgreSQL Cluster

```yaml
postgresql_name: 'postgresql-ha'
postgresql_replicas: 3
postgresql_storage_size: '100Gi'
postgresql_wal_storage_size: '20Gi'
postgresql_memory_limit: '2Gi'
postgresql_cpu_limit: '2'
postgresql_password: 'secure-password-here'
```

### Redis with Authentication

```yaml
redis_name: 'redis-secure'
redis_password_enabled: true
redis_password: 'secure-password'
redis_storage_size: '20Gi'
redis_memory_limit: '1Gi'
```

### MariaDB with Custom Configuration

```yaml
mariadb_name: 'mariadb-prod'
mariadb_replicas: 1
mariadb_storage_size: '100Gi'
mariadb_charset: 'utf8mb4'
mariadb_collation: 'utf8mb4_unicode_ci'
mariadb_config_name: 'mariadb-prod-config'
```

### Valkey with TLS

```yaml
valkey_name: 'valkey-secure'
valkey_tls_enabled: true
valkey_password_enabled: true
valkey_password: 'secure-password'
valkey_tls_cert: 'base64-encoded-certificate'
valkey_tls_key: 'base64-encoded-key'
valkey_ca_cert: 'base64-encoded-ca'
```

## Health Checks and Probes

All StatefulSets include comprehensive health checks:

### Liveness Probe
- Detects container crashes
- Initial delay: 30 seconds
- Period: 10 seconds
- Timeout: 5 seconds
- Failure threshold: 3 attempts

### Readiness Probe
- Determines if pod is ready for traffic
- Initial delay: 5 seconds
- Period: 5 seconds
- Timeout: 5 seconds
- Failure threshold: 3 attempts

## Resource Management

Default resource requests and limits:

| Service  | Memory Request | Memory Limit | CPU Request | CPU Limit |
|----------|---------------|--------------|------------|-----------|
| PostgreSQL | 256Mi | 512Mi | 100m | 500m |
| Redis | 128Mi | 256Mi | 50m | 200m |
| MariaDB | 256Mi | 512Mi | 100m | 500m |
| Valkey | 128Mi | 256Mi | 50m | 200m |

Adjust based on your workload and cluster capacity.

## Security Considerations

### Built-in Security Features

1. **Non-root containers**: All containers run as UID 999
2. **Read-only filesystem**: Init scripts mounted as read-only
3. **Capability dropping**: All Linux capabilities removed
4. **Security context**: Enforced for all workloads
5. **Secret management**: Credentials in Kubernetes Secrets
6. **TLS support**: Available for all services

### Best Practices

1. **Use separate namespaces** for different environments
2. **Enable RBAC** for secret access control
3. **Rotate passwords regularly** using secret updates
4. **Use managed TLS** for encrypted connections
5. **Monitor pod activity** with security policies
6. **Backup critical data** regularly
7. **Use network policies** to restrict traffic
8. **Scan images** for vulnerabilities

## Persistent Storage

### Volume Claims

Each StatefulSet creates persistent volume claims (PVCs):
- PostgreSQL: 10Gi (data) + 5Gi (WAL)
- Redis: 5Gi
- MariaDB: 10Gi
- Valkey: 5Gi

### Storage Classes

Customize storage with the `storage_class` variable:
```yaml
storage_class: 'fast-ssd'  # Fast SSD for performance
storage_class: 'standard'   # Standard storage (default)
storage_class: 'slow-hdd'   # Cost-effective HDD
```

## Monitoring and Observability

### Prometheus Metrics

All services expose Prometheus metrics:
- PostgreSQL: Port 9187 (via postgres_exporter)
- Redis: Port 6379 (native metrics)
- MariaDB: Port 3306 (via mysqld_exporter)
- Valkey: Port 6379 (native metrics)

Add service monitors for Prometheus scraping:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgresql-monitor
spec:
  selector:
    matchLabels:
      app: postgresql
  endpoints:
    - port: metrics
      interval: 30s
```

### Logs and Debugging

View pod logs:
```bash
kubectl logs statefulset/postgresql -f
kubectl logs pod/postgresql-0 -c postgresql -f
```

Describe resource status:
```bash
kubectl describe statefulset postgresql
kubectl get pvc
kubectl get events
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod postgresql-0

# Check events
kubectl get events --sort-by='.lastTimestamp'

# Check logs
kubectl logs postgresql-0
```

### Volume Issues

```bash
# Check PVC status
kubectl get pvc
kubectl describe pvc postgresql-storage-postgresql-0

# Check storage class
kubectl get storageclass
```

### Connection Issues

```bash
# Test connectivity
kubectl exec -it postgresql-0 -- psql -U postgres -d postgres

# Check service DNS
kubectl exec -it pod-name -- nslookup postgresql-headless
```

## Template Variables Reference

### Common Variables
- `namespace`: Kubernetes namespace (default: 'default')
- `storage_class`: Storage class name (default: 'standard')
- `application_name`: Application identifier (default: 'nest-app')

### Service-Specific Variables
- `{service}_name`: StatefulSet and service names
- `{service}_replicas`: Number of replicas (default: 1)
- `{service}_image`: Container image (includes tag)
- `{service}_storage_size`: Persistent volume size
- `{service}_memory_request/limit`: Memory allocation
- `{service}_cpu_request/limit`: CPU allocation
- `{service}_secret_name`: Associated secret name
- `{service}_password`: Service password
- `{service}_password_enabled`: Enable password protection

## Future Enhancements

- [ ] Backup and restore templates
- [ ] Horizontal Pod Autoscaler (HPA) examples
- [ ] Network policies for traffic control
- [ ] Service mesh integration (Istio)
- [ ] GitOps integration (Flux/ArgoCD)
- [ ] Database migration templates
- [ ] Monitoring and alerting rules

## Support and Documentation

For more information:
- Kubernetes StatefulSets: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- PostgreSQL: https://www.postgresql.org/docs/
- Redis: https://redis.io/documentation
- MariaDB: https://mariadb.com/docs/
- Valkey: https://valkey.io/

## License

Limited AGPL3 with preamble for fair use
