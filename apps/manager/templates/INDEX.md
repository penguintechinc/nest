# Kubernetes Database Templates - Index

Complete index and navigation guide for the Nest database provisioning templates.

## Quick Navigation

### For First-Time Users
1. Start with [README.md](README.md) - Overview of all templates
2. Review [VARIABLES.md](VARIABLES.md) - Understand available configuration
3. Check [EXAMPLES.md](EXAMPLES.md) - See real-world configuration examples
4. Use [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Deploy with confidence

### For Quick Deployment
1. Copy a configuration from [EXAMPLES.md](EXAMPLES.md)
2. Customize values in your `values.yaml`
3. Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
4. Deploy with Helm or kubectl

### For Troubleshooting
1. Check [README.md](README.md) - Troubleshooting section
2. Review [EXAMPLES.md](EXAMPLES.md) - Common patterns
3. Verify [VARIABLES.md](VARIABLES.md) - Variable correctness
4. Check pod logs: `kubectl logs pod-name -n namespace`

## File Structure

```
templates/
├── statefulset/              # StatefulSet Kubernetes manifests
│   ├── postgresql.yaml       # PostgreSQL database (25 lines of config + 150 service/statefulset)
│   ├── redis.yaml            # Redis cache
│   ├── mariadb.yaml          # MariaDB SQL database
│   └── valkey.yaml           # Valkey Redis alternative
├── secrets/                  # Secret Kubernetes manifests
│   ├── postgresql-secret.yaml    # PostgreSQL credentials
│   ├── redis-secret.yaml         # Redis configuration
│   ├── mariadb-secret.yaml       # MariaDB credentials
│   ├── valkey-secret.yaml        # Valkey credentials and TLS
│   └── tls-secret.yaml           # TLS certificates
├── deployments/              # Placeholder for application deployments
├── README.md                 # Complete template documentation (552 lines)
├── EXAMPLES.md               # Practical configuration examples (611 lines)
├── VARIABLES.md              # Complete variable reference (493 lines)
├── DEPLOYMENT_CHECKLIST.md   # Pre/during/post-deployment checklist
└── INDEX.md                  # This file

```

## Documentation Files

### README.md (552 lines)
Comprehensive documentation including:
- Directory structure overview
- Detailed StatefulSet template descriptions
- Secret template descriptions
- Deployment usage instructions
- Configuration examples
- Health check information
- Security considerations
- Storage information
- Monitoring and observability
- Troubleshooting guide

**Best for**: Understanding how everything works, reference guide

### EXAMPLES.md (611 lines)
Real-world configuration examples including:
- Quick start examples (minimal, development, production HA)
- Database initialization scripts
- TLS certificate generation
- Helm values file structure
- Deployment scripts
- Environment-specific configurations
- CI/CD integration
- Troubleshooting examples

**Best for**: Getting started, adapting configurations for your needs

### VARIABLES.md (493 lines)
Complete variable reference including:
- Global variables
- PostgreSQL variables (deployment, storage, database, resources)
- Redis variables (deployment, storage, auth, resources)
- MariaDB variables (deployment, storage, database, resources)
- Valkey variables (deployment, storage, auth, TLS, resources)
- TLS variables
- Usage examples
- Best practices
- Variable validation
- Common patterns
- Troubleshooting variable issues

**Best for**: Understanding what each variable does, proper configuration

### DEPLOYMENT_CHECKLIST.md
Comprehensive deployment checklist with:
- Pre-deployment planning
- Configuration preparation
- Cluster preparation
- Pre-deployment testing
- Deployment execution
- Post-deployment verification
- Security verification
- Monitoring setup
- Backup configuration
- Documentation requirements
- Success criteria
- Rollback procedures

**Best for**: Ensuring successful deployment, catching issues early

## Template Files Overview

### StatefulSet Templates

#### postgresql.yaml (175 lines)
PostgreSQL relational database StatefulSet

**Key Components**:
- Headless Service for stable network identity
- StatefulSet with configurable replicas
- Dual volume claims (data + WAL storage)
- Container with PostgreSQL image
- Environment variables from secrets
- Health checks (liveness + readiness)
- Security context (non-root user)
- Pod anti-affinity for HA

**Variables**: 20+ (name, replicas, image, storage, database, user, password, resources, etc.)

**Use When**: You need a relational database with ACID compliance

---

#### redis.yaml (155 lines)
Redis in-memory cache StatefulSet

**Key Components**:
- Headless Service for StatefulSet discovery
- StatefulSet with AOF persistence
- Single volume claim for storage
- Container with Redis image
- Health checks via redis-cli
- Optional password authentication
- Security context (non-root user)
- Pod anti-affinity for distribution

**Variables**: 14+ (name, replicas, image, storage, password, resources, etc.)

**Use When**: You need fast caching with persistence

---

#### mariadb.yaml (168 lines)
MariaDB MySQL-compatible database StatefulSet

**Key Components**:
- Headless Service for stable identity
- StatefulSet with configurable replicas
- Single volume claim for data
- Container with MariaDB image
- Environment variables from secrets
- Health checks via mysqladmin
- Support for init scripts
- Security context (non-root user)
- Pod anti-affinity for HA

**Variables**: 17+ (name, replicas, image, storage, database, user, password, charset, collation, resources)

**Use When**: You need MySQL-compatible database with advanced features

---

#### valkey.yaml (191 lines)
Valkey Redis alternative StatefulSet

**Key Components**:
- Headless Service for discovery
- StatefulSet with configurable replicas
- Single volume claim for storage
- Container with Valkey image
- Optional TLS/mTLS support
- Optional password protection
- Health checks via valkey-cli
- Pod anti-affinity for distribution
- Conditional TLS configuration

**Variables**: 18+ (name, replicas, image, storage, password, tls_enabled, tls certs, resources, etc.)

**Use When**: You need Redis alternative with TLS encryption support

### Secret Templates

#### postgresql-secret.yaml (28 lines)
PostgreSQL credentials and connection strings

**Contains**:
- Database name, username, password
- Root password
- Connection URL (postgresql://user:pass@host:5432/db)
- Connection parameters (host, port, db)
- SSL/TLS configuration

**Variables**: 7 (database, user, password, root_password, host, port, sslmode)

---

#### redis-secret.yaml (34 lines)
Redis authentication and configuration

**Contains**:
- Password (if authentication enabled)
- Connection URLs (with and without auth)
- Connection parameters (host, port, database)
- Configuration flags (auth-enabled, aof-enabled)

**Variables**: 8 (password, host, port, database, auth_enabled, aof_enabled, protocol, etc.)

---

#### mariadb-secret.yaml (29 lines)
MariaDB credentials and connection strings

**Contains**:
- Database name, username, password
- Root password
- Connection URL (mysql://user:pass@host:3306/db)
- Connection parameters (host, port, db)
- Character set and collation

**Variables**: 8 (database, user, password, root_password, host, port, charset, collation)

---

#### valkey-secret.yaml (66 lines)
Valkey credentials and TLS secrets

**Contains**:
- Password (if authentication enabled)
- Connection URLs (standard and TLS variants)
- Connection parameters (host, port, database, tls_port)
- Configuration flags (auth-enabled, tls-enabled)
- Optional: Embedded TLS secrets

**Variables**: 12+ (password, host, port, database, auth_enabled, tls_enabled, tls certs, ca cert)

---

#### tls-secret.yaml (53 lines)
TLS certificates for encrypted connections

**Contains Three Secrets**:
1. `database-tls` - Server TLS certificate and key
2. `database-ca` - CA certificate and key
3. `database-mtls-client` - Client certificate and key

**Variables**: 6 (tls_secret_name, ca_secret_name, mtls_secret_name, tls_cert, tls_key, ca_cert, ca_key, client_cert, client_key)

## Services Comparison

| Service | Database Type | Port | Persistence | TLS Support | Password | HA Support |
|---------|---------------|------|-------------|-------------|----------|-----------|
| PostgreSQL | Relational (SQL) | 5432 | RDB + WAL | Yes | Yes | Yes (3+) |
| Redis | In-Memory Cache | 6379 | AOF/RDB | No | Optional | Yes (3+) |
| MariaDB | Relational (MySQL) | 3306 | InnoDB | Optional | Yes | Yes (3+) |
| Valkey | In-Memory Cache | 6379 | AOF/RDB | Yes | Optional | Yes (3+) |

## Common Tasks

### Deploy PostgreSQL
1. Create values file with PostgreSQL settings
2. Run: `helm template nest ./templates -f values.yaml | kubectl apply -f -`
3. Verify: `kubectl get pods -l app=postgresql`

### Secure Valkey with TLS
1. Generate TLS certificates
2. Encode to base64: `cat tls.crt | base64 -w0`
3. Set variables: `valkey_tls_enabled: true`, `valkey_tls_cert: "..."`
4. Deploy as normal

### High Availability PostgreSQL
1. Set `postgresql_replicas: 3`
2. Set appropriate `storage_size` and resource limits
3. Deploy to same cluster
4. PostgreSQL replication handles synchronization

### Custom Database Initialization
1. Create SQL script file
2. Create ConfigMap: `kubectl create configmap postgresql-init-scripts --from-file=init.sql`
3. Reference in template: `postgresql_init_scripts_config: postgresql-init-scripts`
4. Initialize automatically on startup

### Change Service Names
1. Update `{{ postgresql_name }}`, `{{ redis_name }}`, etc. in values
2. Services and StatefulSets will use new names
3. Update connection strings in applications

## Variable Organization

### Global (3 variables)
- `namespace` - Kubernetes namespace
- `storage_class` - Storage class for PVCs
- `application_name` - App identifier

### PostgreSQL (20 variables)
- Deployment: name, replicas, image
- Storage: size (data + WAL)
- Database: name, user, password, root_password
- Resources: memory/CPU (request + limit)
- Configuration: SSL mode, secret/config names

### Redis (14 variables)
- Deployment: name, replicas, image
- Storage: size
- Authentication: password_enabled, password
- Resources: memory/CPU (request + limit)
- Configuration: secret name, protocol

### MariaDB (17 variables)
- Deployment: name, replicas, image
- Storage: size
- Database: name, user, password, root_password
- Configuration: charset, collation
- Resources: memory/CPU (request + limit)
- Configuration: secret/config names

### Valkey (18 variables)
- Deployment: name, replicas, image
- Storage: size
- Authentication: password_enabled, password
- TLS: tls_enabled, tls_cert, tls_key, ca_cert
- Resources: memory/CPU (request + limit)
- Configuration: secret names, protocol

### TLS (9 variables)
- Secret names: tls, ca, mtls
- Certificate data: tls_cert, tls_key, ca_cert, ca_key, client_cert, client_key

## Deployment Paths

### Path 1: Development Environment
1. Read: README.md (overview)
2. Copy: Example from EXAMPLES.md (development setup)
3. Customize: VARIABLES.md section for each service
4. Deploy: Follow DEPLOYMENT_CHECKLIST.md

### Path 2: Production HA Cluster
1. Plan: Review README.md security section
2. Design: Use EXAMPLES.md (production HA setup)
3. Configure: Reference VARIABLES.md for all options
4. Test: Run through DEPLOYMENT_CHECKLIST.md twice
5. Deploy: Follow checklist step-by-step

### Path 3: Specific Service
1. Find: Service-specific section in README.md
2. Learn: VARIABLES.md section for that service
3. Example: Matching example in EXAMPLES.md
4. Deploy: Isolated deployment following checklist

## Feature Support Matrix

### PostgreSQL
- ✓ High Availability (3+ replicas)
- ✓ Persistence (dual volumes: data + WAL)
- ✓ SSL/TLS encryption
- ✓ Health checks (liveness + readiness)
- ✓ Resource limits/requests
- ✓ Init scripts
- ✓ Non-root security context
- ✓ Pod anti-affinity

### Redis
- ✓ Persistence (AOF + RDB)
- ✓ Optional password protection
- ✓ Health checks (liveness + readiness)
- ✓ Resource limits/requests
- ✓ Non-root security context
- ✓ Pod anti-affinity

### MariaDB
- ✓ High Availability (3+ replicas possible)
- ✓ Persistence (InnoDB storage)
- ✓ Configurable charset/collation
- ✓ Health checks (liveness + readiness)
- ✓ Resource limits/requests
- ✓ Init scripts
- ✓ Non-root security context
- ✓ Pod anti-affinity

### Valkey
- ✓ Persistence (AOF + RDB)
- ✓ Optional password protection
- ✓ TLS/mTLS encryption
- ✓ Health checks (liveness + readiness)
- ✓ Resource limits/requests
- ✓ Non-root security context
- ✓ Pod anti-affinity

## Performance Considerations

### For Development
- Single replica is fine
- 256Mi memory limits acceptable
- Standard storage class suitable
- No TLS needed

### For Staging
- 2 replicas for HA testing
- 512Mi memory limits
- Standard storage adequate
- Optional TLS for testing

### For Production
- 3+ replicas for true HA
- 1Gi+ memory limits depending on workload
- Fast SSD storage recommended
- TLS/mTLS required
- Regular backups essential

## Monitoring Integration

All templates include Prometheus metrics endpoints:

**PostgreSQL**: Port 9187 (postgres_exporter)
**Redis**: Port 6379 (built-in metrics)
**MariaDB**: Port 3306 (mysqld_exporter)
**Valkey**: Port 6379 (built-in metrics)

Add ServiceMonitor or Prometheus scrape config for metrics collection.

## Next Steps

1. **Understand**: Read README.md cover-to-cover
2. **Plan**: Use EXAMPLES.md to find your scenario
3. **Configure**: Reference VARIABLES.md for each variable
4. **Verify**: Follow DEPLOYMENT_CHECKLIST.md
5. **Deploy**: Execute checklist steps
6. **Monitor**: Setup metrics collection
7. **Backup**: Configure backup strategy
8. **Document**: Record your deployment details

## Support Resources

- **Kubernetes**: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- **PostgreSQL**: https://www.postgresql.org/docs/
- **Redis**: https://redis.io/documentation
- **MariaDB**: https://mariadb.com/docs/
- **Valkey**: https://valkey.io/

## Version Information

- **Templates Version**: 1.0.0
- **Created**: 2025-12-24
- **Last Updated**: 2025-12-24
- **Kubernetes Minimum**: 1.20
- **PostgreSQL Image**: 16-alpine
- **Redis Image**: 7-alpine
- **MariaDB Image**: 11-jammy
- **Valkey Image**: 7-alpine

---

**Start here**: Read [README.md](README.md) first, then follow to the relevant documentation based on your needs.
