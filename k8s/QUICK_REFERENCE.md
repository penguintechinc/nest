# Kubernetes Deployment Quick Reference

## Common Commands

### Deployment

```bash
# Deploy to dev
./deploy.sh --env dev

# Deploy to production
./deploy.sh --env prod --method helm

# Dry-run before deploying
./deploy.sh --env prod --dry-run

# Deploy without storage
./deploy.sh --env staging --skip-storage
```

### Monitoring

```bash
# Watch logs from app
./logs.sh --component nest --follow

# View latest 50 lines
./logs.sh --component nest --tail 50

# View all pod logs
./logs.sh --all-pods --follow

# Check logs from previous container
./logs.sh --pod <POD_NAME> --previous
```

### Access & Port Forwarding

```bash
# List available services
./port-forward.sh --list

# Forward to service (auto port)
./port-forward.sh --service nest

# Forward to specific port
./port-forward.sh --service nest --local-port 8080 --remote-port 8080

# Forward to pod
./port-forward.sh --pod <POD_NAME> --pod-port 8080 --local-port 8080
```

### Updates

```bash
# Update image
./update.sh --component nest --image myrepo/nest:v1.2.3

# Rollback
./update.sh --component nest --rollback

# View update history
./update.sh --component nest --history
```

### Cleanup

```bash
# Remove deployment
./undeploy.sh --env dev

# Force remove without confirmation
./undeploy.sh --env dev --force

# Keep namespace after removal
./undeploy.sh --env dev --keep-namespace
```

## Kubectl Alternatives

If you prefer kubectl directly:

```bash
# Deploy
kubectl apply -f manifests/

# View logs
kubectl logs -f deployment/nest -n nest-dev

# Port forward
kubectl port-forward svc/nest 8080:8080 -n nest-dev

# Restart deployment
kubectl rollout restart deployment/nest -n nest-dev

# View events
kubectl get events -n nest-dev --sort-by='.lastTimestamp'

# Describe pod
kubectl describe pod <POD_NAME> -n nest-dev

# Execute command in pod
kubectl exec -it <POD_NAME> -n nest-dev -- /bin/bash
```

## Helm Alternatives

```bash
# Install release
helm install nest ./helm/nest -n nest-dev --create-namespace

# Upgrade release
helm upgrade nest ./helm/nest -n nest-dev

# Rollback release
helm rollback nest -n nest-dev

# View release history
helm history nest -n nest-dev

# Get values
helm get values nest -n nest-dev
```

## Troubleshooting

```bash
# Check pod status
kubectl get pods -n nest-dev

# Describe problematic pod
kubectl describe pod <POD_NAME> -n nest-dev

# Check resource usage
kubectl top pods -n nest-dev

# View cluster nodes
kubectl get nodes

# Check node status
kubectl describe node <NODE_NAME>

# View all resources
kubectl get all -n nest-dev

# Export state for backup
kubectl get all -n nest-dev -o yaml > backup.yaml
```

## Environment Variables

Use these environment variables to override defaults:

```bash
# Set environment
export ENV=prod

# Set deployment method
export METHOD=kubectl

# Set namespace
export NAMESPACE=custom-nest-namespace

# Enable dry-run mode
export DRY_RUN=true

# Then run scripts without arguments
./deploy.sh
```

## Useful Aliases

Add to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
alias kn='kubectl -n nest-dev'
alias kl='./k8s/logs.sh --follow'
alias kp='./k8s/port-forward.sh --list'
alias kd='./k8s/deploy.sh --env dev'
alias ku='./k8s/undeploy.sh --env dev'

# Quick log access
alias logs-nest='./k8s/logs.sh --component nest --follow'
alias logs-mgmt='./k8s/logs.sh --component management --follow'
alias logs-all='./k8s/logs.sh --all-pods --follow'
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Cluster connection fails | Check kubeconfig: `kubectl config current-context` |
| Pod stuck pending | Check events: `kubectl describe pod <POD>` |
| Image pull error | Verify image exists and registry access |
| Port already in use | Use auto port detection without `--local-port` |
| Rollout timeout | Increase timeout: `./update.sh --timeout 600` |
| Helm release conflict | Delete old release: `helm delete nest -n nest-dev` |

## Script Behavior

### Exit Codes

- `0` - Success
- `1` - General error or validation failure
- `2` - Missing prerequisites (kubectl, helm)
- `126+` - Command execution errors

### Dry-Run Mode

All scripts support `--dry-run` to preview changes:

```bash
./deploy.sh --env prod --dry-run
```

This shows what would happen without making actual changes.

### Confirmation Prompts

Destructive operations require confirmation:

```bash
# Interactive (prompts for confirmation)
./undeploy.sh --env prod

# Automated (no prompts)
./undeploy.sh --env prod --force
```

## Color Codes

Scripts use these color codes:

- GREEN `[INFO]` - Informational messages
- YELLOW `[WARN]` - Warnings and important notices
- RED `[ERROR]` - Errors and failures
- BLUE `[DEBUG]` - Debug information

## Getting Help

Each script includes detailed help:

```bash
./deploy.sh --help
./undeploy.sh --help
./update.sh --help
./logs.sh --help
./port-forward.sh --help
```

Read the full README for comprehensive documentation:

```bash
cat README.md
```
