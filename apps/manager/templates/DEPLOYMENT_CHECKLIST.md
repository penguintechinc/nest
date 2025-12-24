# Database Templates - Deployment Checklist

Use this checklist to ensure a successful deployment of database services.

## Pre-Deployment Planning

### Environment Selection
- [ ] Identify target environment (development/staging/production)
- [ ] Determine namespace for deployment
- [ ] Check available storage classes in cluster
- [ ] Verify cluster resource availability

### Requirements Analysis
- [ ] List required database services
  - [ ] PostgreSQL (relational database)
  - [ ] Redis (in-memory cache)
  - [ ] MariaDB (MySQL-compatible database)
  - [ ] Valkey (Redis alternative)
- [ ] Calculate storage requirements
  - [ ] Current data size
  - [ ] Expected growth (next 12 months)
  - [ ] Buffer for operations (20-30%)
- [ ] Estimate resource requirements
  - [ ] CPU cores needed
  - [ ] Memory (RAM) needed
  - [ ] Network bandwidth

### Security Planning
- [ ] Generate strong passwords (20+ chars, mixed case, numbers, symbols)
- [ ] Decide on authentication method
  - [ ] Password-based (default)
  - [ ] TLS/mTLS encryption
  - [ ] Both
- [ ] Plan for credential rotation strategy
- [ ] Determine backup strategy
- [ ] Plan for disaster recovery

## Configuration Preparation

### Create Values File
- [ ] Copy template values file
- [ ] Set namespace
- [ ] Select storage class
- [ ] Configure PostgreSQL
  - [ ] Service name
  - [ ] Replicas (1 for dev, 2+ for HA)
  - [ ] Storage size (data + WAL)
  - [ ] Database name
  - [ ] Username
  - [ ] Password (strong!)
  - [ ] Resource limits
- [ ] Configure Redis
  - [ ] Service name
  - [ ] Replicas
  - [ ] Storage size
  - [ ] Password (if needed)
  - [ ] Resource limits
- [ ] Configure MariaDB (if needed)
  - [ ] Service name
  - [ ] Database name
  - [ ] Username
  - [ ] Root password
  - [ ] Character set
- [ ] Configure Valkey (if needed)
  - [ ] TLS enabled/disabled
  - [ ] Password enabled/disabled
  - [ ] Certificate data (if TLS)

### Generate Certificates (if using TLS)
- [ ] Generate self-signed certificates or obtain from CA
  ```bash
  bash generate-tls-certs.sh
  ```
- [ ] Encode certificates to base64
  ```bash
  cat tls.crt | base64 -w0
  ```
- [ ] Add to values file or secret

### Initialize Scripts (Optional)
- [ ] Create initialization SQL/script files
- [ ] Create ConfigMap for scripts
  ```bash
  kubectl create configmap postgresql-init-scripts \
    --from-file=init.sql
  ```
- [ ] Reference ConfigMap in values

## Cluster Preparation

### Kubernetes Cluster
- [ ] Verify cluster connectivity
  ```bash
  kubectl cluster-info
  kubectl get nodes
  ```
- [ ] Check cluster version compatibility (K8s 1.20+)
- [ ] Verify RBAC is enabled
- [ ] Check available storage

### Namespace Setup
- [ ] Create target namespace
  ```bash
  kubectl create namespace {{ namespace }}
  ```
- [ ] Apply namespace labels (optional)
  ```bash
  kubectl label namespace {{ namespace }} env=production
  ```
- [ ] Configure resource quotas (optional)
- [ ] Configure network policies (optional)

### Storage Class Verification
- [ ] List available storage classes
  ```bash
  kubectl get storageclass
  ```
- [ ] Verify storage class exists for selected class
- [ ] Check provisioner (aws-ebs, ceph, etc.)
- [ ] Verify enough storage capacity available
- [ ] Test PVC creation (optional)

## Pre-Deployment Testing

### Template Validation
- [ ] Validate YAML syntax
  ```bash
  helm template nest ./templates -f values.yaml | kubectl apply -f - --dry-run=client
  ```
- [ ] Check for Jinja2 rendering errors
- [ ] Verify all variables are substituted
- [ ] Look for template warnings

### Permission Verification
- [ ] Check RBAC permissions for service account
- [ ] Verify secret creation permissions
- [ ] Confirm StatefulSet creation permissions
- [ ] Test namespace access

### Network Verification
- [ ] Verify DNS is working in cluster
  ```bash
  kubectl run -it --rm debug --image=alpine --restart=Never -- nslookup kubernetes.default
  ```
- [ ] Check network policies don't block required traffic
- [ ] Verify port availability

## Deployment Execution

### Deploy Secrets
- [ ] Review secret contents (without exposing passwords)
  ```bash
  helm template nest ./templates -f values.yaml | grep -A 20 "kind: Secret"
  ```
- [ ] Deploy secrets
  ```bash
  kubectl apply -f secrets/postgresql-secret.yaml -n {{ namespace }}
  ```
- [ ] Verify secrets created
  ```bash
  kubectl get secrets -n {{ namespace }}
  ```

### Deploy Services
- [ ] Deploy headless services
  ```bash
  kubectl apply -f statefulset/postgresql.yaml -n {{ namespace }}
  ```
- [ ] Verify services created
  ```bash
  kubectl get svc -n {{ namespace }}
  ```

### Monitor Pod Startup
- [ ] Watch pod creation
  ```bash
  kubectl get pods -n {{ namespace }} -w
  ```
- [ ] Check initialization progress
  ```bash
  kubectl logs -n {{ namespace }} postgresql-0 -f
  ```
- [ ] Verify no errors in logs
- [ ] Wait for all pods to be ready

## Post-Deployment Verification

### Pod Status Verification
- [ ] All pods running
  ```bash
  kubectl get pods -n {{ namespace }}
  ```
- [ ] All pods ready (1/1 status)
- [ ] No pods in CrashLoopBackOff state
- [ ] No pending pods

### Resource Verification
- [ ] Persistent volumes created
  ```bash
  kubectl get pv -n {{ namespace }}
  ```
- [ ] Persistent volume claims bound
  ```bash
  kubectl get pvc -n {{ namespace }}
  ```
- [ ] Correct storage size allocated
- [ ] ConfigMaps created (if using init scripts)

### Network Verification
- [ ] Services have cluster IPs
  ```bash
  kubectl get svc -n {{ namespace }}
  ```
- [ ] Headless service has no cluster IP
- [ ] DNS names resolve
  ```bash
  kubectl run -it --rm debug --image=alpine --restart=Never -- \
    nslookup postgresql.{{ namespace }}.svc.cluster.local
  ```

### Service Connectivity Tests

#### PostgreSQL
- [ ] Port 5432 is open
- [ ] pg_isready succeeds
  ```bash
  kubectl exec -it postgresql-0 -n {{ namespace }} -- \
    pg_isready -U {{ postgresql_user }}
  ```
- [ ] Connect to database
  ```bash
  kubectl exec -it postgresql-0 -n {{ namespace }} -- \
    psql -U {{ postgresql_user }} -d {{ postgresql_database }}
  ```
- [ ] Run test query
  ```sql
  SELECT 1;
  ```

#### Redis
- [ ] Port 6379 is open
- [ ] Redis responds to ping
  ```bash
  kubectl exec -it redis-0 -n {{ namespace }} -- redis-cli ping
  ```
- [ ] Connect and test
  ```bash
  kubectl exec -it redis-0 -n {{ namespace }} -- redis-cli
  > SET test-key "hello"
  > GET test-key
  ```

#### MariaDB
- [ ] Port 3306 is open
- [ ] mysqladmin ping succeeds
  ```bash
  kubectl exec -it mariadb-0 -n {{ namespace }} -- \
    mysqladmin ping -u root -p${MARIADB_ROOT_PASSWORD}
  ```
- [ ] Connect to database
  ```bash
  kubectl exec -it mariadb-0 -n {{ namespace }} -- \
    mysql -u {{ mariadb_user }} -p{{ mariadb_password }} \
    -D {{ mariadb_database }}
  ```

#### Valkey
- [ ] Port 6379 is open
- [ ] Valkey responds to ping
  ```bash
  kubectl exec -it valkey-0 -n {{ namespace }} -- valkey-cli ping
  ```
- [ ] Test key operations
  ```bash
  kubectl exec -it valkey-0 -n {{ namespace }} -- valkey-cli
  > SET mykey "hello"
  > GET mykey
  ```

### Health Check Verification
- [ ] Liveness probes succeeding
  ```bash
  kubectl get pods -n {{ namespace }} -o jsonpath='{.items[*].status.containerStatuses[*].livenessProbe}'
  ```
- [ ] Readiness probes succeeding
  ```bash
  kubectl get pods -n {{ namespace }} -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")]}'
  ```
- [ ] No probe failures in events
  ```bash
  kubectl get events -n {{ namespace }}
  ```

### Data Persistence Verification
- [ ] Data survives pod restart (for critical databases)
- [ ] Test write and verify after restart
  ```bash
  # Write data
  kubectl exec postgresql-0 -n {{ namespace }} -- \
    psql -U {{ postgresql_user }} -d {{ postgresql_database }} \
    -c "CREATE TABLE test (id SERIAL, data TEXT)"

  # Restart pod
  kubectl delete pod postgresql-0 -n {{ namespace }}
  kubectl wait --for=condition=ready pod postgresql-0 -n {{ namespace }}

  # Verify data
  kubectl exec postgresql-0 -n {{ namespace }} -- \
    psql -U {{ postgresql_user }} -d {{ postgresql_database }} \
    -c "SELECT * FROM test"
  ```

## Security Verification

### Authentication Verification
- [ ] Default credentials changed (if applicable)
- [ ] Passwords are strong and unique
- [ ] No plaintext passwords in manifests
- [ ] Secrets are stored in Kubernetes Secrets

### Access Control Verification
- [ ] RBAC policies are properly configured
- [ ] Service accounts have minimal permissions
- [ ] Network policies restrict traffic (if configured)
- [ ] Only authorized users can access secrets

### TLS Verification (if enabled)
- [ ] TLS certificates are valid
  ```bash
  openssl x509 -in tls.crt -text -noout
  ```
- [ ] Certificates are not expired
- [ ] Connections use TLS/mTLS
- [ ] Certificate validation working

## Monitoring Setup

### Prometheus Metrics
- [ ] Prometheus endpoints are accessible
  - PostgreSQL: Port 9187
  - Redis: Port 6379
  - MariaDB: Port 3306
  - Valkey: Port 6379
- [ ] Metrics are being collected
  ```bash
  kubectl port-forward pod/postgresql-0 9187:9187 -n {{ namespace }}
  curl http://localhost:9187/metrics
  ```
- [ ] ServiceMonitor is created (if using Prometheus Operator)

### Logging Setup
- [ ] Pod logs are accessible
  ```bash
  kubectl logs -f pod/postgresql-0 -n {{ namespace }}
  ```
- [ ] Logs are being collected by log aggregation service
- [ ] No error messages in logs

### Alerting Setup
- [ ] Alert rules are configured
- [ ] Alerting targets are verified
- [ ] Test alert delivery

## Backup Configuration

### Backup Strategy
- [ ] Backup schedule is defined
- [ ] Backup tool is configured
- [ ] Backup storage location is prepared
- [ ] Backup retention policy is set

### Backup Verification
- [ ] First backup completed successfully
- [ ] Backup is stored in correct location
- [ ] Backup size is reasonable
- [ ] Backup can be restored (test)

## Documentation

### Update Project Documentation
- [ ] Document deployed services
- [ ] Document connection strings
- [ ] Document credentials (securely, encrypted)
- [ ] Document backup procedures
- [ ] Document troubleshooting steps
- [ ] Document disaster recovery procedures

### Team Communication
- [ ] Notify team of deployment
- [ ] Share connection information securely
- [ ] Provide access instructions
- [ ] Update runbooks/playbooks

## Performance Baseline

### Establish Baseline Metrics
- [ ] Record initial CPU usage
- [ ] Record initial memory usage
- [ ] Record initial storage usage
- [ ] Record network throughput
- [ ] Record query performance

### Load Testing (Optional)
- [ ] Run load test against databases
- [ ] Verify performance meets requirements
- [ ] Check for bottlenecks
- [ ] Adjust resources if needed

## Common Issues and Troubleshooting

### If Pods Don't Start
- [ ] Check pod events
  ```bash
  kubectl describe pod postgresql-0 -n {{ namespace }}
  ```
- [ ] Check logs
  ```bash
  kubectl logs postgresql-0 -n {{ namespace }}
  ```
- [ ] Check PVC status
  ```bash
  kubectl describe pvc postgresql-storage-postgresql-0 -n {{ namespace }}
  ```
- [ ] Check storage class exists
  ```bash
  kubectl get storageclass
  ```

### If Pods Can't Connect
- [ ] Check service exists
  ```bash
  kubectl get svc -n {{ namespace }}
  ```
- [ ] Test DNS resolution
  ```bash
  kubectl run -it --rm debug --image=alpine --restart=Never -- \
    nslookup postgresql-headless.{{ namespace }}.svc.cluster.local
  ```
- [ ] Test port accessibility
  ```bash
  kubectl run -it --rm debug --image=alpine --restart=Never -- \
    nc -zv postgresql.{{ namespace }}.svc.cluster.local 5432
  ```

### If Data Is Lost
- [ ] Check PVC status
- [ ] Check pod termination messages
- [ ] Check storage backend (cloud provider)
- [ ] Restore from backup (if available)

## Post-Deployment Tasks

### Cleanup and Optimization
- [ ] Remove temporary files
- [ ] Clean up debug resources
- [ ] Optimize resource limits based on actual usage
- [ ] Update documentation with actual metrics

### Maintenance Planning
- [ ] Schedule regular backups
- [ ] Plan credential rotation
- [ ] Schedule security updates
- [ ] Plan capacity management reviews
- [ ] Setup maintenance windows

### Monitoring and Alerting
- [ ] Create dashboard for databases
- [ ] Setup critical alerts
- [ ] Setup warning alerts
- [ ] Test alert channels
- [ ] Document alert response procedures

## Success Criteria

All of the following should be true for successful deployment:

- [ ] All pods are running and ready
- [ ] All services are accessible
- [ ] All connectivity tests pass
- [ ] Health checks are passing
- [ ] Data persistence is working
- [ ] Credentials are secure
- [ ] Backups are functioning
- [ ] Monitoring is collecting metrics
- [ ] Documentation is complete
- [ ] Team is trained and informed

## Rollback Procedure

If deployment fails or needs to be rolled back:

1. [ ] Scale StatefulSet to 0
   ```bash
   kubectl scale statefulset postgresql --replicas=0 -n {{ namespace }}
   ```

2. [ ] Delete StatefulSet (keeps PVC)
   ```bash
   kubectl delete statefulset postgresql -n {{ namespace }}
   ```

3. [ ] Verify PVCs are preserved
   ```bash
   kubectl get pvc -n {{ namespace }}
   ```

4. [ ] Fix issues in values/templates

5. [ ] Reapply templates
   ```bash
   helm template nest ./templates -f values.yaml | kubectl apply -f -
   ```

6. [ ] Verify recovery

## Additional Resources

- README.md - Comprehensive documentation
- EXAMPLES.md - Configuration examples
- VARIABLES.md - Variable reference
- Kubernetes StatefulSet docs: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- PostgreSQL docs: https://www.postgresql.org/docs/
- Redis docs: https://redis.io/documentation
- MariaDB docs: https://mariadb.com/docs/
- Valkey docs: https://valkey.io/

## Approval Sign-Off

After completing all items, get approval from:

- [ ] DevOps/Platform Team Lead
- [ ] Security Team
- [ ] Database Administrator
- [ ] Application Owner

Date Deployed: _________________
Deployed By: _________________
Approved By: _________________

---

Last Updated: 2025-12-24
Template Version: 1.0.0
