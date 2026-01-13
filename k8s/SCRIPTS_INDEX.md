# Kubernetes Deployment Scripts Index

Quick navigation guide for all deployment automation scripts.

## Core Deployment Scripts

### deploy.sh - Deploy to Kubernetes
**File**: `/home/penguin/code/Nest/k8s/deploy.sh`

Primary deployment orchestration script.

```bash
./deploy.sh --env dev --method helm
./deploy.sh --env prod --dry-run
./deploy.sh --skip-storage --skip-management
```

**Key Features**:
- Support for dev, staging, prod environments
- Helm and kubectl deployment methods
- Dry-run mode for testing
- Granular control with --skip-* options
- Automatic prerequisite validation
- Full deployment verification

**See**: `README.md` - Full deployment guide

---

### undeploy.sh - Remove Deployment
**File**: `/home/penguin/code/Nest/k8s/undeploy.sh`

Safe cleanup and removal of all Nest resources.

```bash
./undeploy.sh --env dev
./undeploy.sh --env prod --force
./undeploy.sh --keep-namespace
```

**Key Features**:
- Removes resources in reverse order
- Safety confirmation prompts
- Namespace preservation option
- Handles both Helm and kubectl resources

**See**: `README.md` - Cleanup section

---

### update.sh - Rolling Updates
**File**: `/home/penguin/code/Nest/k8s/update.sh`

Perform rolling updates, rollbacks, and track version history.

```bash
./update.sh --component nest --image myrepo/nest:v1.2.3
./update.sh --component nest --rollback
./update.sh --component nest --history
```

**Key Features**:
- Rolling updates with health verification
- Automatic rollback on failure
- Deployment history tracking
- Component-specific updates
- Configurable rollout parameters

**See**: `README.md` - Updates section

---

### logs.sh - View Pod Logs
**File**: `/home/penguin/code/Nest/k8s/logs.sh`

Access and tail logs from pods with filtering and formatting.

```bash
./logs.sh --component nest --follow
./logs.sh --all-pods --tail 50
./logs.sh --pod <POD_NAME> --previous
```

**Key Features**:
- Component-based log filtering
- Live log following
- Multiple pod log aggregation
- Previous container instance logs
- Customizable formatting

**See**: `README.md` - Logs section

---

### port-forward.sh - Local Service Access
**File**: `/home/penguin/code/Nest/k8s/port-forward.sh`

Forward ports to access cluster services locally.

```bash
./port-forward.sh --service nest
./port-forward.sh --component management --remote-port 9090
./port-forward.sh --list
```

**Key Features**:
- Service and pod port forwarding
- Auto-detection of available ports
- Service/pod discovery
- Development and debugging access

**See**: `README.md` - Port Forward section

---

## Documentation Files

### README.md
**Comprehensive deployment documentation**

- Quick start guide
- Prerequisites and installation
- Detailed script documentation
- Configuration management
- Troubleshooting guide
- Best practices
- Advanced usage examples

**Start Here**: This is the main reference document.

---

### QUICK_REFERENCE.md
**Quick command reference**

- Common commands cheat sheet
- kubectl and helm alternatives
- Environment variables
- Useful shell aliases
- Common issues and solutions

**Use For**: Quick lookup of frequently used commands

---

## Common Tasks

### Deploy Application
```bash
# Development
./k8s/deploy.sh --env dev

# Production (preview first)
./k8s/deploy.sh --env prod --dry-run
./k8s/deploy.sh --env prod
```

### Monitor Deployment
```bash
# Watch application logs
./k8s/logs.sh --component nest --follow

# Watch all pods
./k8s/logs.sh --all-pods --follow
```

### Update Application
```bash
# Deploy new version
./k8s/update.sh --component nest --image myrepo/nest:v2.0.0

# Rollback if needed
./k8s/update.sh --component nest --rollback
```

### Access Service Locally
```bash
# List available services
./k8s/port-forward.sh --list

# Forward to service
./k8s/port-forward.sh --service nest --local-port 8080
```

### Remove Deployment
```bash
# Interactive cleanup
./k8s/undeploy.sh --env dev

# Force cleanup without prompts
./k8s/undeploy.sh --env dev --force
```

---

## Help & Documentation

### Get Help from Scripts
```bash
# Get help for any script
./deploy.sh --help
./undeploy.sh --help
./update.sh --help
./logs.sh --help
./port-forward.sh --help
```

### Read Documentation
```bash
# Main documentation
cat README.md

# Quick reference
cat QUICK_REFERENCE.md

# This index
cat SCRIPTS_INDEX.md
```

---

## Troubleshooting Quick Links

- **Cluster connection fails**: See README.md → Troubleshooting → Cluster Connection Fails
- **Pod not starting**: See README.md → Troubleshooting → Deployment Issues
- **Image pull errors**: See README.md → Troubleshooting → Deployment Issues
- **Logs not showing**: See README.md → Troubleshooting → Rollback Issues
- **Port already in use**: See QUICK_REFERENCE.md → Common Issues & Solutions

---

## File Sizes & Locations

| File | Size | Type |
|------|------|------|
| deploy.sh | 8.9K | Bash Script |
| undeploy.sh | 4.7K | Bash Script |
| update.sh | 6.5K | Bash Script |
| logs.sh | 5.1K | Bash Script |
| port-forward.sh | 6.9K | Bash Script |
| README.md | 12K | Documentation |
| QUICK_REFERENCE.md | 4.9K | Documentation |
| SCRIPTS_INDEX.md | This file | Documentation |

**Total**: ~55KB of production-ready automation and documentation

---

## First Time Setup

1. **Make scripts executable** (already done):
   ```bash
   chmod +x /home/penguin/code/Nest/k8s/*.sh
   ```

2. **Check prerequisites**:
   ```bash
   kubectl version --client
   helm version
   ```

3. **Verify cluster access**:
   ```bash
   kubectl cluster-info
   kubectl get nodes
   ```

4. **Read the README**:
   ```bash
   cat /home/penguin/code/Nest/k8s/README.md
   ```

5. **Try a test deployment**:
   ```bash
   ./k8s/deploy.sh --env dev --dry-run
   ```

---

## Integration with CI/CD

These scripts are designed for CI/CD pipelines:

```bash
# In GitHub Actions, GitLab CI, Jenkins, etc.

# Deploy to staging on merge
./k8s/deploy.sh --env staging

# Update production image
./k8s/update.sh --env prod --component nest --image $IMAGE_TAG

# Verify deployment
./k8s/logs.sh --env prod --component nest --tail 10
```

---

## Environment Variables

Override defaults with environment variables:

```bash
export ENV=prod
export METHOD=kubectl
export DRY_RUN=true

./deploy.sh  # Uses exported values
```

---

## Additional Resources

- **Kubernetes Documentation**: https://kubernetes.io/docs
- **Helm Documentation**: https://helm.sh/docs
- **kubectl Cheat Sheet**: https://kubernetes.io/docs/reference/kubectl/cheatsheet
- **Nest Project**: Check project root README.md
- **Support**: support@penguintech.io

---

## Version

Scripts created for Nest deployment automation.
Compatible with Kubernetes 1.24+ and Helm 3.0+.

Last Updated: 2025-01-09
