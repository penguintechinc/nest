# NEST Monitoring Stack

Comprehensive Kubernetes monitoring solution for the NEST project using Prometheus, Grafana, AlertManager, and rsyslog.

## Overview

This monitoring stack provides:
- **Metrics Collection**: Prometheus for scraping and storing metrics
- **Visualization**: Grafana dashboards for system and application monitoring
- **Alerting**: AlertManager for intelligent alert routing and notifications
- **Centralized Logging**: rsyslog for syslog aggregation and forwarding

## Directory Structure

```
infrastructure/monitoring/
├── namespace.yaml                 # Monitoring namespace definition
├── prometheus/
│   ├── values.yaml               # Helm values for Prometheus
│   ├── configmap.yaml            # Prometheus scrape configuration
│   └── servicemonitor.yaml       # ServiceMonitor and PrometheusRules
├── grafana/
│   ├── values.yaml               # Helm values for Grafana
│   ├── datasources.yaml          # Prometheus datasource config
│   └── dashboards/
│       ├── nest-overview.json    # System overview dashboard
│       └── nest-resources.json   # Resource monitoring dashboard
├── alertmanager/
│   ├── values.yaml               # Helm values for AlertManager
│   └── config.yaml               # Alert routing and receivers
├── rsyslog/
│   ├── configmap.yaml            # rsyslog configuration
│   ├── service.yaml              # rsyslog services (ClusterIP, NodePort, LoadBalancer)
│   └── deployment.yaml           # rsyslog deployment with Prometheus exporter
├── deploy.sh                      # Automated deployment script
└── README.md                      # This file
```

## Prerequisites

### Required Tools
- **kubectl**: >= 1.24
- **helm**: >= 3.10
- **Kubernetes cluster**: >= 1.24

### Required Permissions
- Cluster admin access
- Ability to create namespaces and ClusterRoles
- Storage provisioning (PVC creation)

### Storage Classes
The stack requires the following storage classes:
- `fast-ssd`: For persistent data (Prometheus, Grafana, rsyslog logs)
- A default storage class if fast-ssd is not available

## Installation

### Quick Start

1. **Deploy the entire monitoring stack:**
   ```bash
   cd infrastructure/monitoring
   ./deploy.sh
   ```

   The script will:
   - Create the `monitoring` namespace
   - Add Helm repositories
   - Deploy Prometheus stack (Prometheus, Grafana, AlertManager)
   - Configure NEST service discovery
   - Deploy rsyslog for log aggregation
   - Verify deployments

2. **Wait for pods to be ready:**
   ```bash
   kubectl get pods -n monitoring -w
   ```

### Manual Installation Steps

#### 1. Create Namespace
```bash
kubectl apply -f infrastructure/monitoring/namespace.yaml
```

#### 2. Add Helm Repositories
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

#### 3. Deploy Prometheus Stack
```bash
helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values infrastructure/monitoring/prometheus/values.yaml \
  --wait
```

#### 4. Apply Prometheus Configuration
```bash
kubectl apply -f infrastructure/monitoring/prometheus/configmap.yaml
kubectl apply -f infrastructure/monitoring/prometheus/servicemonitor.yaml
```

#### 5. Deploy Grafana Dashboards
```bash
kubectl apply -f infrastructure/monitoring/grafana/datasources.yaml

# Create dashboard ConfigMaps
kubectl create configmap grafana-dashboard-nest-overview \
  --from-file=infrastructure/monitoring/grafana/dashboards/nest-overview.json \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

kubectl label configmap grafana-dashboard-nest-overview \
  grafana_dashboard=1 -n monitoring --overwrite
```

#### 6. Deploy AlertManager Configuration
```bash
kubectl apply -f infrastructure/monitoring/alertmanager/config.yaml
```

#### 7. Deploy rsyslog
```bash
kubectl apply -f infrastructure/monitoring/rsyslog/configmap.yaml
kubectl apply -f infrastructure/monitoring/rsyslog/service.yaml
kubectl apply -f infrastructure/monitoring/rsyslog/deployment.yaml
```

## Configuration

### Prometheus

#### Service Discovery
Prometheus automatically discovers NEST services through Kubernetes labels:

**Required pod labels:**
```yaml
labels:
  app: nest-api        # or nest-manager, nest-web
  prometheus: enabled
```

**Metrics endpoint requirements:**
- Port: `9090`, `9091`, or `3000` (configurable per service)
- Path: `/metrics`
- Format: Prometheus text format

#### Scrape Configuration
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retention**: 15 days
- **Storage**: 100GB default (adjustable in values.yaml)

#### Adding New Service Monitors
Create a new ServiceMonitor for auto-discovery:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-service
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: my-service
  endpoints:
    - port: metrics
      interval: 30s
```

### Grafana

#### Access
- **URL**: `http://localhost:3000` (via port-forward)
- **Default username**: admin
- **Default password**: admin

**Change password on first login!**

#### Port-Forward
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
```

#### Dashboards
Pre-configured dashboards available:
- **NEST System Overview**: Service status and request rates
- **NEST Resource Monitoring**: CPU, memory, network, and restart metrics

#### Adding Custom Dashboards
Place JSON dashboard files in `grafana/dashboards/` and create ConfigMaps:

```bash
kubectl create configmap grafana-dashboard-custom \
  --from-file=grafana/dashboards/custom.json \
  -n monitoring --dry-run=client -o yaml | kubectl apply -f -

kubectl label configmap grafana-dashboard-custom \
  grafana_dashboard=1 -n monitoring --overwrite
```

### AlertManager

#### Configuration
Alert routing is configured in `alertmanager/config.yaml`:

**Default routes:**
- Platform team alerts → platform@nest.local
- Backend team alerts → backend@nest.local
- Critical alerts → PagerDuty

#### Available Notifications
- **Email**: SMTP configuration
- **PagerDuty**: On-call escalation
- **Slack**: Channel notifications (optional)
- **Webhook**: Custom integrations

#### Configuring Email Notifications
Update `alertmanager/config.yaml`:

```yaml
receivers:
  - name: "platform-team"
    email_configs:
      - to: "platform@nest.local"
        from: "alertmanager@nest.local"
        smarthost: "smtp.example.com:587"
        auth_username: "user@example.com"
        auth_password: "password"
```

Then apply:
```bash
kubectl apply -f infrastructure/monitoring/alertmanager/config.yaml
```

#### Viewing Alerts
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
# Access: http://localhost:9093
```

### rsyslog

#### Service Access
rsyslog provides three service types:

**1. ClusterIP (internal)**
```bash
kubectl port-forward -n monitoring svc/rsyslog 514:514 --address=0.0.0.0
# Legacy syslog: localhost:514 (UDP/TCP)
```

**2. NodePort (node-level access)**
- UDP: Node IP:30514
- TCP: Node IP:31514

**3. LoadBalancer (external access)**
- Requires external load balancer
- UDP/TCP: LoadBalancer IP:514

#### Sending Logs to rsyslog

**From Kubernetes pods:**
```bash
logger -n rsyslog.monitoring.svc.cluster.local -P 514 "message"
```

**From external systems:**
```bash
# Get LoadBalancer IP
kubectl get svc rsyslog-loadbalancer -n monitoring
# Send syslog to that IP:514
```

#### Log Files
Logs stored in `/var/log/nest/`:
- `syslog`: All messages
- `auth.log`: Authentication logs
- `kernel.log`: Kernel messages
- `applications.log`: Application logs (local0)
- `api.log`: API logs (local3)

#### Configuring Log Forwarding
Edit `rsyslog/configmap.yaml` and uncomment forwarding section:

```yaml
action(type="omfwd"
    target="syslog.example.com"
    port="514"
    protocol="tcp"
    streamDriver="gtls"
    streamDriverMode="1")
```

Then apply:
```bash
kubectl apply -f infrastructure/monitoring/rsyslog/configmap.yaml
kubectl rollout restart deployment rsyslog -n monitoring
```

## Monitoring Alerts

### Pre-configured Alert Rules

#### Critical Alerts
- **ServiceDown**: Service not responding for > 2 minutes
- **CriticalCPUUsage**: Pod CPU > 95% for > 2 minutes
- **CriticalMemoryUsage**: Pod memory > 95% of limit for > 2 minutes
- **DiskSpaceCritical**: Less than 5% disk space available

#### Warning Alerts
- **HighCPUUsage**: Pod CPU > 80% for > 5 minutes
- **HighMemoryUsage**: Pod memory > 80% of limit for > 5 minutes
- **HighErrorRate**: 5xx error rate > 5% for > 5 minutes
- **SlowResponseTime**: p95 response time > 1 second for > 5 minutes
- **DiskSpaceWarning**: Less than 20% disk space available

#### Information Alerts
- **PodRestarting**: Pod restarts detected in last 15 minutes

### Testing Alerts

Test alert firing:
```bash
# Port-forward to Prometheus
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090

# Execute PromQL query in UI
up{job="nest-api"} == 0
```

## Maintenance

### Backup

**Backup Grafana dashboards:**
```bash
kubectl exec -n monitoring \
  $(kubectl get pod -n monitoring -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}') \
  -c grafana -- \
  grafana-cli admin export-dashboard > dashboards_backup.json
```

**Backup Prometheus configuration:**
```bash
kubectl get configmap -n monitoring prometheus-config -o yaml > prometheus_backup.yaml
```

### Updates

**Update Helm chart:**
```bash
helm repo update
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f infrastructure/monitoring/prometheus/values.yaml
```

**Restart deployments:**
```bash
kubectl rollout restart deployment -n monitoring
```

### Cleaning Up

**Delete entire monitoring stack:**
```bash
helm uninstall kube-prometheus-stack -n monitoring
kubectl delete namespace monitoring
```

**Delete specific component:**
```bash
# AlertManager
kubectl delete statefulset -n monitoring kube-prometheus-stack-alertmanager

# rsyslog
kubectl delete deployment -n monitoring rsyslog
kubectl delete pvc -n monitoring rsyslog-logs-pvc
```

## Troubleshooting

### Prometheus not scraping metrics

1. **Check service discovery:**
   ```bash
   kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
   # Check Targets tab in Prometheus UI
   ```

2. **Verify ServiceMonitor:**
   ```bash
   kubectl get servicemonitor -n monitoring
   kubectl describe servicemonitor nest-api -n monitoring
   ```

3. **Check pod labels:**
   ```bash
   kubectl get pods --show-labels -A | grep nest
   ```

### Grafana dashboards not loading

1. **Check ConfigMaps:**
   ```bash
   kubectl get configmap -n monitoring | grep dashboard
   ```

2. **Verify labels:**
   ```bash
   kubectl get configmap -n monitoring --show-labels | grep grafana_dashboard
   ```

3. **Check Grafana logs:**
   ```bash
   kubectl logs -n monitoring -l app.kubernetes.io/name=grafana -f
   ```

### AlertManager not sending notifications

1. **Check configuration:**
   ```bash
   kubectl get configmap -n monitoring alertmanager-config -o yaml
   ```

2. **Verify secrets:**
   ```bash
   kubectl get secret -n monitoring alertmanager-secrets
   ```

3. **Check AlertManager logs:**
   ```bash
   kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager -f
   ```

### rsyslog not receiving logs

1. **Check service:**
   ```bash
   kubectl get svc rsyslog -n monitoring
   kubectl get endpoints rsyslog -n monitoring
   ```

2. **Check pods:**
   ```bash
   kubectl logs -n monitoring -l app=rsyslog -f
   ```

3. **Test connectivity:**
   ```bash
   kubectl run -it --image=alpine test-syslog --rm -- \
     sh -c 'echo "test" | nc -u rsyslog.monitoring.svc.cluster.local 514'
   ```

### PVC not binding

1. **Check storage class:**
   ```bash
   kubectl get storageclass
   ```

2. **Check PVC status:**
   ```bash
   kubectl get pvc -n monitoring
   kubectl describe pvc -n monitoring
   ```

3. **Create storage class if missing:**
   ```bash
   kubectl apply -f - <<EOF
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: fast-ssd
   provisioner: kubernetes.io/no-provisioner
   allowVolumeExpansion: true
   EOF
   ```

## Performance Tuning

### Prometheus

**Increase retention:**
```bash
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --set prometheus.prometheusSpec.retention=30d \
  --set prometheus.prometheusSpec.retentionSize=200Gi
```

**Increase resource limits:**
```bash
helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --set prometheus.prometheusSpec.resources.limits.cpu=4 \
  --set prometheus.prometheusSpec.resources.limits.memory=8Gi
```

### Grafana

**Increase panel refresh rate:**
- Edit dashboard → change refresh interval at top

**Optimize queries:**
- Use recording rules in Prometheus to pre-calculate complex metrics

### rsyslog

**Increase queue size:**
Edit `rsyslog/configmap.yaml` and modify queue parameters:
```yaml
queue.maxDiskSpace="5g"
queue.type="linkedList"
```

## Security Considerations

1. **Change default passwords:**
   ```bash
   kubectl set env deployment/kube-prometheus-stack-grafana \
     -n monitoring \
     GF_SECURITY_ADMIN_PASSWORD=<strong-password>
   ```

2. **Enable HTTPS:**
   - Configure TLS in ingress annotations
   - Use cert-manager for certificate management

3. **Restrict access:**
   - Set ingress auth (nginx.ingress.kubernetes.io/auth-*)
   - Use NetworkPolicies to restrict traffic

4. **Secure AlertManager:**
   - Store credentials in Kubernetes Secrets
   - Rotate SMTP and API credentials regularly

5. **Log retention:**
   - Configure log rotation in rsyslog
   - Set retention policies based on compliance requirements

## Support & Resources

- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/grafana/latest/
- **AlertManager Docs**: https://prometheus.io/docs/alerting/latest/alertmanager/
- **rsyslog Docs**: https://www.rsyslog.com/doc/
- **Kubernetes Monitoring**: https://kubernetes.io/docs/tasks/debug-application-cluster/resource-metrics-pipeline/

## Version Information

- **Helm Chart**: prometheus-community/kube-prometheus-stack v54.2.2
- **Prometheus**: v2.50.0
- **Grafana**: 10.2.0
- **AlertManager**: v0.26.0
- **rsyslog**: 8.2310.0

## Contributing

To add new monitoring capabilities:

1. **Add PrometheusRules** in `prometheus/servicemonitor.yaml`
2. **Create new Grafana dashboards** in `grafana/dashboards/`
3. **Update AlertManager routes** in `alertmanager/config.yaml`
4. **Test in development cluster** before production deployment

## License

Limited AGPL3 with preamble for fair use - See LICENSE.md at project root
