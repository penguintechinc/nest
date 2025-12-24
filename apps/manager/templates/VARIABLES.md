# Kubernetes Database Templates - Variable Reference

Complete reference for all Jinja2 template variables used in the StatefulSet and Secret templates.

## Global Variables

These variables apply to all templates and services.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `namespace` | string | `default` | Kubernetes namespace for all resources |
| `storage_class` | string | `standard` | StorageClass name for persistent volumes |
| `application_name` | string | `nest-app` | Application identifier for labels and metadata |

## PostgreSQL Variables

### Deployment Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `postgresql_name` | string | `postgresql` | StatefulSet and service name |
| `postgresql_replicas` | integer | `1` | Number of PostgreSQL replicas |
| `postgresql_image` | string | `postgres:16-alpine` | Container image with tag |

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `postgresql_storage_size` | string | `10Gi` | Size of main data volume |
| `postgresql_wal_storage_size` | string | `5Gi` | Size of WAL (Write-Ahead Log) volume |

### Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `postgresql_database` | string | `postgres` | Default database name |
| `postgresql_user` | string | `postgres` | Database user (non-root) |
| `postgresql_password` | string | `` | Database user password |
| `postgresql_root_password` | string | `` | Superuser password |
| `postgresql_sslmode` | string | `prefer` | SSL mode: disable, allow, prefer, require |

### Resource Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `postgresql_memory_request` | string | `256Mi` | Memory request for container |
| `postgresql_memory_limit` | string | `512Mi` | Memory limit for container |
| `postgresql_cpu_request` | string | `100m` | CPU request (millicores) |
| `postgresql_cpu_limit` | string | `500m` | CPU limit (millicores) |

### Secret and Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `postgresql_secret_name` | string | `postgresql-secret` | Name of secret with credentials |
| `postgresql_init_scripts_config` | string | `postgresql-init-scripts` | ConfigMap name for init scripts |

## Redis Variables

### Deployment Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_name` | string | `redis` | StatefulSet and service name |
| `redis_replicas` | integer | `1` | Number of Redis replicas |
| `redis_image` | string | `redis:7-alpine` | Container image with tag |

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_storage_size` | string | `5Gi` | Size of persistent volume |

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_password_enabled` | boolean | `false` | Enable password authentication |
| `redis_password` | string | `` | Redis password (if enabled) |

### Resource Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_memory_request` | string | `128Mi` | Memory request for container |
| `redis_memory_limit` | string | `256Mi` | Memory limit for container |
| `redis_cpu_request` | string | `50m` | CPU request (millicores) |
| `redis_cpu_limit` | string | `200m` | CPU limit (millicores) |

### Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_secret_name` | string | `redis-secret` | Name of secret with credentials |
| `redis_protocol` | string | `redis` | Protocol name for URLs |

## MariaDB Variables

### Deployment Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `mariadb_name` | string | `mariadb` | StatefulSet and service name |
| `mariadb_replicas` | integer | `1` | Number of MariaDB replicas |
| `mariadb_image` | string | `mariadb:11-jammy` | Container image with tag |

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `mariadb_storage_size` | string | `10Gi` | Size of persistent volume |

### Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `mariadb_database` | string | `mariadb` | Default database name |
| `mariadb_user` | string | `mariadb` | Database user |
| `mariadb_password` | string | `` | Database user password |
| `mariadb_root_password` | string | `` | Root user password |
| `mariadb_charset` | string | `utf8mb4` | Default character set |
| `mariadb_collation` | string | `utf8mb4_unicode_ci` | Default collation |

### Resource Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `mariadb_memory_request` | string | `256Mi` | Memory request for container |
| `mariadb_memory_limit` | string | `512Mi` | Memory limit for container |
| `mariadb_cpu_request` | string | `100m` | CPU request (millicores) |
| `mariadb_cpu_limit` | string | `500m` | CPU limit (millicores) |

### Secret and Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `mariadb_secret_name` | string | `mariadb-secret` | Name of secret with credentials |
| `mariadb_config_name` | string | `mariadb-config` | ConfigMap name for configuration |
| `mariadb_init_scripts_config` | string | `mariadb-init-scripts` | ConfigMap name for init scripts |

## Valkey Variables

### Deployment Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_name` | string | `valkey` | StatefulSet and service name |
| `valkey_replicas` | integer | `1` | Number of Valkey replicas |
| `valkey_image` | string | `valkey/valkey:7-alpine` | Container image with tag |

### Storage Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_storage_size` | string | `5Gi` | Size of persistent volume |

### Authentication

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_password_enabled` | boolean | `false` | Enable password authentication |
| `valkey_password` | string | `` | Valkey password (if enabled) |

### TLS Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_tls_enabled` | boolean | `false` | Enable TLS/encryption |
| `valkey_tls_cert` | string | `base64-encoded` | Base64-encoded TLS certificate |
| `valkey_tls_key` | string | `base64-encoded` | Base64-encoded TLS private key |
| `valkey_ca_cert` | string | `base64-encoded` | Base64-encoded CA certificate |

### Resource Limits

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_memory_request` | string | `128Mi` | Memory request for container |
| `valkey_memory_limit` | string | `256Mi` | Memory limit for container |
| `valkey_cpu_request` | string | `50m` | CPU request (millicores) |
| `valkey_cpu_limit` | string | `200m` | CPU limit (millicores) |

### Secret and Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `valkey_secret_name` | string | `valkey-secret` | Name of secret with credentials |
| `valkey_tls_secret_name` | string | `valkey-tls` | Name of TLS secret |
| `valkey_protocol` | string | `valkey` | Protocol name for URLs |

## TLS Certificate Variables

### General TLS Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `tls_secret_name` | string | `database-tls` | Name of TLS secret |
| `ca_secret_name` | string | `database-ca` | Name of CA certificate secret |
| `mtls_secret_name` | string | `database-mtls-client` | Name of mTLS client secret |

### Certificate Data

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `tls_cert` | string | `base64-encoded` | Base64-encoded server certificate |
| `tls_key` | string | `base64-encoded` | Base64-encoded server private key |
| `ca_cert` | string | `base64-encoded` | Base64-encoded CA certificate |
| `ca_key` | string | `base64-encoded` | Base64-encoded CA private key |
| `client_cert` | string | `base64-encoded` | Base64-encoded client certificate |
| `client_key` | string | `base64-encoded` | Base64-encoded client private key |

## Variable Usage Examples

### Minimal Configuration

```yaml
namespace: default
postgresql_name: postgres
postgresql_database: myapp
postgresql_password: mypassword
```

### Development Configuration

```yaml
namespace: development
storage_class: standard

postgresql_name: postgres-dev
postgresql_replicas: 1
postgresql_storage_size: 5Gi
postgresql_database: dev_db
postgresql_user: dev_user
postgresql_password: dev_pass123

redis_name: redis-dev
redis_replicas: 1
redis_password_enabled: false
redis_storage_size: 1Gi
```

### Production Configuration

```yaml
namespace: production
storage_class: fast-ssd

postgresql_name: postgresql-prod
postgresql_replicas: 3
postgresql_storage_size: 500Gi
postgresql_wal_storage_size: 100Gi
postgresql_memory_limit: 2Gi
postgresql_cpu_limit: 2
postgresql_database: prod_db
postgresql_user: prod_user
postgresql_password: "{{ vault['postgresql_password'] }}"
postgresql_root_password: "{{ vault['postgresql_root_password'] }}"
postgresql_sslmode: require

redis_name: redis-prod
redis_replicas: 3
redis_password_enabled: true
redis_password: "{{ vault['redis_password'] }}"
redis_memory_limit: 1Gi
redis_cpu_limit: 1

valkey_name: valkey-prod
valkey_tls_enabled: true
valkey_password_enabled: true
valkey_password: "{{ vault['valkey_password'] }}"
valkey_tls_cert: "{{ vault['valkey_cert'] }}"
valkey_tls_key: "{{ vault['valkey_key'] }}"
valkey_ca_cert: "{{ vault['valkey_ca'] }}"
```

## Best Practices for Variables

### Security

1. **Never commit passwords in plain text** - Use vault, secrets management, or environment substitution
2. **Use strong passwords** - Minimum 20 characters with mixed case, numbers, and symbols
3. **Rotate credentials regularly** - Update secrets in Kubernetes without redeploying
4. **Separate secrets from configuration** - Keep sensitive data in separate secret files

```bash
# Generate secure passwords
openssl rand -base64 32

# Create secrets from environment
kubectl create secret generic postgresql-secret \
  --from-literal=password=$(openssl rand -base64 32) \
  -n default
```

### Naming Conventions

1. **Use descriptive names** - Include environment and service in name
   - Good: `postgresql-prod`, `redis-staging`, `mariadb-dev`
   - Bad: `db`, `cache`, `service1`

2. **Consistent naming** - Use same pattern across all services
   - All PostgreSQL: `postgresql-*`
   - All Redis: `redis-*`
   - All MariaDB: `mariadb-*`

3. **Namespace isolation** - Use namespace-specific names
   - `postgresql-prod` in `production` namespace
   - `postgresql-staging` in `staging` namespace

### Resource Management

1. **Set appropriate limits** - Based on expected workload
   - Small deployments: request=128Mi, limit=256Mi
   - Medium deployments: request=512Mi, limit=1Gi
   - Large deployments: request=2Gi, limit=4Gi

2. **CPU allocation** - Ensure sufficient CPU for performance
   - Databases: minimum 100m (0.1 cores)
   - Cache stores: minimum 50m (0.05 cores)
   - Production: at least 500m-1 CPU

3. **Storage sizing** - Plan for growth
   - Add 20-30% overhead for operations
   - PostgreSQL WAL: 10-20% of main storage
   - Cache: based on working set size

### Replica Strategy

1. **Development**: 1 replica (cost-effective)
2. **Staging**: 2 replicas (testing HA)
3. **Production**: 3+ replicas (true high availability)

```yaml
# Development
postgresql_replicas: 1

# Staging
postgresql_replicas: 2

# Production
postgresql_replicas: 3
```

## Variable Validation

### Required Variables

Ensure these variables are always set:

```yaml
# Essential for all templates
namespace: ""            # Must not be empty
storage_class: ""        # Should match cluster storage

# Service-specific (when service is enabled)
postgresql_database: ""  # Required for PostgreSQL
postgresql_password: ""  # Required for PostgreSQL
```

### Type Checking

Variables with type constraints:

```yaml
# Strings - enclose in quotes
postgresql_sslmode: "require"
mariadb_charset: "utf8mb4"

# Integers - no quotes for numbers
postgresql_replicas: 3
redis_replicas: 1

# Booleans - lowercase true/false
redis_password_enabled: true
valkey_tls_enabled: false

# Base64 strings - long encoded values
tls_cert: "LS0tLS1CRUdJTi..."
```

## Environment Variable Substitution

### Docker Environment Variables

```bash
# In your .env file or CI/CD pipeline
export POSTGRESQL_PASSWORD=my-secure-password
export REDIS_PASSWORD=another-secure-password
export NAMESPACE=production

# Reference in values file
postgresql_password: "${POSTGRESQL_PASSWORD}"
redis_password: "${REDIS_PASSWORD}"
namespace: "${NAMESPACE}"
```

### Kubernetes ConfigMap References

```yaml
# Instead of direct values
postgresql_password: !include ./secrets/postgresql-password.txt

# Or in Helm
postgresql_password: {{ .Values.secrets.postgresql.password }}
```

## Common Patterns

### HA Database Cluster

```yaml
postgresql_name: postgresql-ha
postgresql_replicas: 3
postgresql_storage_size: 100Gi
postgresql_memory_limit: 2Gi
postgresql_cpu_limit: 2
postgresql_sslmode: require
```

### Secure Cache with TLS

```yaml
valkey_name: valkey-secure
valkey_tls_enabled: true
valkey_password_enabled: true
valkey_password: secure-password
valkey_memory_limit: 1Gi
```

### Cost-Optimized Development

```yaml
namespace: development
storage_class: standard
postgresql_storage_size: 5Gi
redis_storage_size: 1Gi
postgresql_memory_limit: 256Mi
redis_memory_limit: 128Mi
```

## Troubleshooting Variable Issues

### Template not rendering

1. Check variable names are spelled correctly
2. Ensure variables match exactly (case-sensitive)
3. Verify YAML syntax in values file
4. Check for missing quotes on string values

```bash
# Test rendering
helm template nest ./templates -f values.yaml | grep postgresql_name
```

### Invalid values

1. Verify storage sizes use valid K8s format (e.g., `10Gi`, `1000Mi`)
2. Confirm resource limits are reasonable for cluster
3. Check password variables are URL-safe if used in connection strings
4. Validate base64 encoding for TLS certificates

```bash
# Validate base64 encoding
echo "YOUR_BASE64_STRING" | base64 -d | head -5
```

### Runtime errors

1. Check actual values substituted in manifests
2. Compare rendered manifest against Kubernetes API
3. Verify secret names match in both StatefulSet and Secret templates

```bash
# View rendered template
helm template nest ./templates -f values.yaml > manifest.yaml
kubectl apply -f manifest.yaml --dry-run=client
```

## Complete Variable Checklist

Use this checklist when deploying:

- [ ] `namespace` is set and exists
- [ ] `storage_class` matches cluster storage classes
- [ ] All required passwords are strong (20+ chars)
- [ ] Database names are valid and unique
- [ ] User names follow database-specific conventions
- [ ] Resource requests are less than limits
- [ ] Storage sizes have proper units (Gi, Mi, etc.)
- [ ] Replica counts match intended HA level
- [ ] Image tags are specified (no `latest`)
- [ ] Secret names don't conflict with existing secrets
- [ ] TLS certificates are valid and not expired
- [ ] All boolean values are lowercase (true/false)
