#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MANAGEMENT_DIR="${SCRIPT_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl first."
    exit 1
fi

# Check cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

log_info "Deploying Nest management cluster components..."

# Deploy namespace and RBAC
log_info "Deploying namespace and RBAC..."
kubectl apply -f "${MANAGEMENT_DIR}/00-namespace.yaml"
kubectl apply -f "${MANAGEMENT_DIR}/01-rbac.yaml"

# Deploy dashboard
log_info "Deploying Kubernetes Dashboard..."
kubectl apply -f "${MANAGEMENT_DIR}/10-dashboard.yaml"

# Deploy monitoring
log_info "Deploying monitoring components..."
if kubectl apply -f "${MANAGEMENT_DIR}/20-monitoring.yaml" 2>/dev/null; then
    log_info "Monitoring components deployed (requires Prometheus operator)"
else
    log_warn "Monitoring deployment failed - ensure Prometheus CRDs are installed"
fi

# Deploy logging
log_info "Deploying logging aggregation..."
kubectl apply -f "${MANAGEMENT_DIR}/30-logging.yaml"

# Deploy backup cronjob
log_info "Deploying database backup cronjob..."
kubectl apply -f "${MANAGEMENT_DIR}/40-backup-cronjob.yaml"

# Deploy cleanup cronjob
log_info "Deploying resource cleanup cronjob..."
kubectl apply -f "${MANAGEMENT_DIR}/41-cleanup-cronjob.yaml"

log_info "Management components deployment completed!"

# Display deployment status
log_info "Deployment Status:"
kubectl get pods -n nest-management
echo ""
log_info "Services in nest-management:"
kubectl get svc -n nest-management
echo ""
log_info "CronJobs in nest-management:"
kubectl get cronjobs -n nest-management

echo ""
log_info "To access Kubernetes Dashboard:"
echo "  kubectl port-forward -n nest-management svc/kubernetes-dashboard 8443:443"
echo "  Open: https://localhost:8443"

exit 0
