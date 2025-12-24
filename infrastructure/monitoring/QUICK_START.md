# NEST Monitoring Stack - Quick Start Guide

## One-Command Deployment

```bash
cd infrastructure/monitoring && ./deploy.sh
```

This single command will:
1. Validate prerequisites (kubectl, helm, cluster connectivity)
2. Create the `monitoring` namespace
3. Add Helm repositories (prometheus-community, grafana)
4. Deploy Prometheus with service discovery for NEST apps
5. Configure Grafana dashboards automatically
6. Set up AlertManager with email notifications
7. Deploy rsyslog for centralized logging
8. Verify all components are running

## Access Monitoring Services

### Prometheus
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090
# Open: http://localhost:9090
# Targets: Status > Targets (check NEST services auto-discovered)
```

### Grafana
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
# Open: http://localhost:3000
# Login: admin / admin (change on first login!)
# Dashboards: Look in "NEST" folder
```

### AlertManager
```bash
kubectl port-forward -n monitoring svc/kube-prometheus-stack-alertmanager 9093:9093
# Open: http://localhost:9093
# Silences: Configure alert suppression
# Alerts: View active alerts
```

### rsyslog
```bash
# For local testing
kubectl port-forward -n monitoring svc/rsyslog 514:514 --address=0.0.0.0

# Send test message
echo "test" | nc -u localhost 514

# View logs in pod
kubectl logs -n monitoring -l app=rsyslog -f
```

## Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n monitoring -o wide

# Check services
kubectl get svc -n monitoring

# Check PVCs are bound
kubectl get pvc -n monitoring

# Check ServiceMonitors
kubectl get servicemonitors -n monitoring

# Describe a specific resource
kubectl describe servicemonitor nest-api -n monitoring
```

## Common Tasks

### Check if NEST services are discovered
1. Port-forward to Prometheus: `kubectl port-forward -n monitoring svc/kube-prometheus-stack-prometheus 9090:9090`
2. Go to Status > Targets
3. Look for job names: `nest-api`, `nest-manager`, `nest-web`
4. Should show "UP" in green

### View logs from a specific component
```bash
# Prometheus
kubectl logs -n monitoring -l app.kubernetes.io/name=prometheus -f

# Grafana
kubectl logs -n monitoring -l app.kubernetes.io/name=grafana -f

# AlertManager
kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager -f

# rsyslog
kubectl logs -n monitoring -l app=rsyslog -f
```

### Update Prometheus configuration
```bash
# Edit the ConfigMap
kubectl edit configmap prometheus-config -n monitoring

# Restart Prometheus to apply changes
kubectl rollout restart statefulset kube-prometheus-stack-prometheus -n monitoring
```

### Update AlertManager configuration
```bash
# Edit AlertManager config
kubectl edit configmap alertmanager-config -n monitoring

# Reload AlertManager
kubectl rollout restart statefulset kube-prometheus-stack-alertmanager -n monitoring
```

### Scale rsyslog replicas
```bash
kubectl scale deployment rsyslog --replicas=5 -n monitoring
```

### Backup Grafana dashboards
```bash
# Export all dashboards
kubectl exec -n monitoring \
  $(kubectl get pod -n monitoring -l app.kubernetes.io/name=grafana -o jsonpath='{.items[0].metadata.name}') \
  -c grafana -- \
  grafana-cli admin export-dashboard > dashboards_backup.json
```

## Troubleshooting

### Services not appearing in Prometheus
1. Check pod labels: `kubectl get pods --show-labels -A | grep nest`
2. Must have labels: `app=nest-api` and `prometheus=enabled`
3. Must expose metrics on port 9090/9091 (configurable)
4. ServiceMonitor must be created: `kubectl get servicemonitor -n monitoring`

### Grafana dashboards not loading
1. Check dashboard ConfigMaps: `kubectl get configmap -n monitoring | grep dashboard`
2. Must be labeled: `grafana_dashboard=1`
3. Restart Grafana: `kubectl rollout restart deployment kube-prometheus-stack-grafana -n monitoring`

### AlertManager not sending emails
1. Check secrets: `kubectl get secret alertmanager-secrets -n monitoring`
2. Verify SMTP config in ConfigMap: `kubectl get configmap alertmanager-config -n monitoring -o yaml`
3. Check logs: `kubectl logs -n monitoring -l app.kubernetes.io/name=alertmanager`
4. Test SMTP connection from pod

### rsyslog not receiving logs
1. Check service endpoints: `kubectl get endpoints rsyslog -n monitoring`
2. Verify pod is running: `kubectl get pods -n monitoring -l app=rsyslog`
3. Test connectivity: `nc -zu localhost 514` (if using port-forward)
4. Check PVC binding: `kubectl get pvc rsyslog-logs-pvc -n monitoring`

## Configuration Files

### Key Configuration Locations

```
infrastructure/monitoring/
├── prometheus/
│   ├── values.yaml          # Helm values (retention, storage, selectors)
│   └── configmap.yaml       # Scrape configs and service discovery
├── grafana/
│   ├── values.yaml          # Helm values (plugins, auth, storage)
│   └── dashboards/          # Dashboard JSON files
├── alertmanager/
│   ├── values.yaml          # Helm values
│   └── config.yaml          # Alert routing, receivers, inhibition
└── rsyslog/
    ├── configmap.yaml       # rsyslog.conf, log forwarding
    └── deployment.yaml      # Pod specs, resources, replicas
```

## Environment-Specific Configuration

### For Production
```bash
# Edit values before deployment
sed -i 's/retention: 15d/retention: 30d/' prometheus/values.yaml
sed -i 's/storage: 100Gi/storage: 500Gi/' prometheus/values.yaml

# Update email recipients
kubectl edit configmap alertmanager-config -n monitoring
```

### For Development
```bash
# Use smaller storage
kubectl set env statefulset kube-prometheus-stack-prometheus \
  -n monitoring \
  RETENTION="7d"
```

## Uninstall

### Remove everything
```bash
# Delete namespace (removes all resources)
kubectl delete namespace monitoring

# Or use Helm
helm uninstall kube-prometheus-stack -n monitoring
```

### Keep Prometheus data
```bash
# Delete deployment but keep PVCs
kubectl delete deployment -n monitoring rsyslog
kubectl delete statefulset -n monitoring kube-prometheus-stack-prometheus

# Data persists in PVCs for recovery
```

## Next Steps

1. **Configure email alerts** - Update SMTP settings in `alertmanager/config.yaml`
2. **Add custom dashboards** - Place JSON files in `grafana/dashboards/` and create ConfigMaps
3. **Create alert rules** - Add PrometheusRules in `prometheus/servicemonitor.yaml`
4. **Set up log forwarding** - Uncomment forwarding section in `rsyslog/configmap.yaml`
5. **Configure ingress** - Update DNS and TLS settings in values files

For detailed information, see [README.md](./README.md)
