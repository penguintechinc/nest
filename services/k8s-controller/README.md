# NEST Kubernetes Controller

A high-performance Kubernetes controller that manages the lifecycle of database and infrastructure resources provisioned by the NEST platform.

## Overview

The NEST Kubernetes Controller implements a full reconciliation loop pattern to ensure that the actual state in Kubernetes matches the desired state stored in the NEST PostgreSQL database. It continuously monitors resources with `lifecycle_mode=full` and performs create, update, scale, and delete operations as needed.

## Features

- **Full Reconciliation Loop**: Continuous monitoring and reconciliation of resource state
- **Event-Driven Updates**: Real-time response to Kubernetes events (Pod/StatefulSet changes)
- **Multi-Worker Architecture**: Concurrent processing with configurable worker count
- **Exponential Backoff**: Automatic retry with backoff for failed operations
- **Audit Logging**: Complete audit trail of all controller operations
- **Health Checks**: Built-in liveness and readiness endpoints
- **Prometheus Metrics**: Exportable metrics for monitoring
- **Graceful Shutdown**: Clean shutdown on SIGTERM/SIGINT

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Controller                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Reconcile    │  │   Event      │  │   Worker     │  │
│  │ Loop         │  │   Handler    │  │   Pool       │  │
│  │              │  │              │  │              │  │
│  │ (30s timer)  │  │ (K8s events) │  │ (5 workers)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
           │                    │
           ├────────────────────┴─────────────────┐
           │                                      │
           ▼                                      ▼
    ┌──────────────┐                      ┌──────────────┐
    │  Reconciler  │                      │   Watcher    │
    │              │                      │              │
    │ - Create     │                      │ - StatefulSets│
    │ - Update     │                      │ - Pods       │
    │ - Delete     │                      │              │
    │ - Scale      │                      │              │
    └──────────────┘                      └──────────────┘
           │                                      │
           ▼                                      │
    ┌──────────────┐                             │
    │  PostgreSQL  │◄────────────────────────────┘
    │   Database   │
    └──────────────┘
```

## Components

### Controller
Main orchestrator that manages the reconciliation loop, event handling, and worker pool.

### Reconciler
Handles the reconciliation logic for individual resources:
- Compares desired state (database) with actual state (Kubernetes)
- Creates/updates/deletes Kubernetes resources
- Updates resource status in database
- Manages provisioning jobs and audit logs

### Watcher
Monitors Kubernetes resources for changes:
- Watches StatefulSets for status updates
- Watches Pods for failures and phase changes
- Sends events to the controller for processing

## Reconciliation Logic

For each resource with `lifecycle_mode=full`:

1. **Query Database**: Fetch resource configuration and desired state
2. **Get K8s State**: Retrieve current StatefulSet/Pod status from Kubernetes
3. **Compare States**: Determine if action is needed
4. **Reconcile**:
   - **Missing in K8s**: Create StatefulSet and related resources
   - **Configuration Drift**: Update StatefulSet spec
   - **Scale Change**: Adjust replica count
   - **Marked for Deletion**: Delete StatefulSet and update status
5. **Update Status**: Write current state back to database
6. **Create Audit Logs**: Record all operations for compliance

## Configuration

Configuration is loaded from environment variables:

### Database Configuration
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `DB_USER`: Database user (default: `nest`)
- `DB_PASSWORD`: Database password (required)
- `DB_NAME`: Database name (default: `nest`)
- `DB_SSL_MODE`: SSL mode (default: `disable`)

### Kubernetes Configuration
- `KUBECONFIG`: Path to kubeconfig file (optional, for out-of-cluster)
- `IN_CLUSTER`: Use in-cluster config (default: `true`)
- `WATCH_ALL_NAMESPACES`: Watch all namespaces (default: `false`)
- `NAMESPACE_PREFIX`: Team namespace prefix (default: `nest-team-`)

### Controller Configuration
- `RECONCILE_INTERVAL`: Reconciliation interval (default: `30s`)
- `WORKER_COUNT`: Number of worker goroutines (default: `5`)
- `MAX_RETRIES`: Maximum retry attempts (default: `3`)
- `BACKOFF_BASE`: Base backoff duration (default: `5s`)
- `BACKOFF_MAX`: Maximum backoff duration (default: `5m`)

### Logging Configuration
- `LOG_LEVEL`: Log level (default: `info`, options: `debug`, `info`, `warn`, `error`)
- `LOG_FORMAT`: Log format (default: `json`, options: `json`, `text`)

### Feature Flags
- `ENABLE_METRICS`: Enable Prometheus metrics (default: `true`)
- `METRICS_PORT`: Metrics server port (default: `9090`)
- `ENABLE_HEALTH_CHECK`: Enable health check endpoint (default: `true`)
- `HEALTH_CHECK_PORT`: Health check server port (default: `8080`)

## Building

### Local Build
```bash
go build -o k8s-controller main.go
```

### Docker Build
```bash
docker build -t nest/k8s-controller:latest \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  .
```

### Multi-Architecture Build
```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t nest/k8s-controller:latest \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
  --push \
  .
```

## Deployment

### Kubernetes Deployment

Create a deployment manifest:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: nest-controller
  namespace: nest-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: nest-controller
rules:
- apiGroups: [""]
  resources: ["namespaces", "pods"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["statefulsets"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: [""]
  resources: ["services", "persistentvolumeclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: nest-controller
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: nest-controller
subjects:
- kind: ServiceAccount
  name: nest-controller
  namespace: nest-system
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nest-controller
  namespace: nest-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nest-controller
  template:
    metadata:
      labels:
        app: nest-controller
    spec:
      serviceAccountName: nest-controller
      containers:
      - name: controller
        image: nest/k8s-controller:latest
        env:
        - name: DB_HOST
          value: "postgresql.nest-system.svc.cluster.local"
        - name: DB_PORT
          value: "5432"
        - name: DB_USER
          value: "nest"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: nest-db-credentials
              key: password
        - name: DB_NAME
          value: "nest"
        - name: IN_CLUSTER
          value: "true"
        - name: LOG_LEVEL
          value: "info"
        - name: RECONCILE_INTERVAL
          value: "30s"
        ports:
        - containerPort: 8080
          name: health
        - containerPort: 9090
          name: metrics
        livenessProbe:
          httpGet:
            path: /healthz
            port: health
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /readyz
            port: health
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

Apply the deployment:

```bash
kubectl apply -f deployment.yaml
```

## Monitoring

### Health Endpoints

- **Liveness**: `http://localhost:8080/healthz`
- **Readiness**: `http://localhost:8080/readyz`

### Metrics Endpoint

Prometheus metrics are available at: `http://localhost:9090/metrics`

### Logs

View controller logs:

```bash
kubectl logs -n nest-system -l app=nest-controller -f
```

## Development

### Prerequisites
- Go 1.23+
- Kubernetes cluster (local or remote)
- PostgreSQL database
- kubectl configured

### Running Locally

1. Set environment variables:
```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=nest
export DB_PASSWORD=your-password
export DB_NAME=nest
export IN_CLUSTER=false
export KUBECONFIG=~/.kube/config
export LOG_LEVEL=debug
```

2. Run the controller:
```bash
go run main.go
```

### Testing

```bash
# Run unit tests
go test ./... -v

# Run with coverage
go test ./... -coverprofile=coverage.out
go tool cover -html=coverage.out
```

## Troubleshooting

### Controller Not Starting
- Check database connectivity
- Verify Kubernetes credentials
- Review logs for error messages

### Resources Not Reconciling
- Check resource `lifecycle_mode` is set to `full`
- Verify namespace exists
- Review controller logs for errors
- Check retry queue for backoff status

### High CPU/Memory Usage
- Reduce `WORKER_COUNT`
- Increase `RECONCILE_INTERVAL`
- Review number of resources being managed

## License

Copyright (c) 2025 Penguin Tech Inc. All rights reserved.

Limited AGPL3 with preamble for fair use. See LICENSE.md for details.
