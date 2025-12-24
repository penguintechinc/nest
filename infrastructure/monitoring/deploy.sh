#!/bin/bash

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="monitoring"
RELEASE_NAME="kube-prometheus-stack"
HELM_REPO_PROMETHEUS="prometheus-community"
HELM_REPO_GRAFANA="grafana"
HELM_CHART="prometheus-community/kube-prometheus-stack"
PROMETHEUS_VERSION="54.2.2"
TIMEOUT="10m"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    log_success "kubectl found: $(kubectl version --client --short 2>/dev/null | grep -o 'v[0-9]*\.[0-9]*\.[0-9]*')"

    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed"
        exit 1
    fi
    log_success "helm found: $(helm version --short 2>/dev/null | grep -o 'v[0-9]*\.[0-9]*\.[0-9]*')"

    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    log_success "Connected to Kubernetes cluster"
}

# Create namespace
create_namespace() {
    log_info "Creating/checking monitoring namespace..."

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace '$NAMESPACE' already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Created namespace '$NAMESPACE'"
    fi

    # Label namespace for monitoring
    kubectl label namespace "$NAMESPACE" \
        monitoring=enabled \
        prometheus-rules=enabled \
        --overwrite &> /dev/null
}

# Add Helm repositories
add_helm_repos() {
    log_info "Adding Helm repositories..."

    # Add prometheus-community repo
    if helm repo list | grep -q "$HELM_REPO_PROMETHEUS"; then
        log_info "Updating existing prometheus-community repository..."
        helm repo update "$HELM_REPO_PROMETHEUS"
    else
        log_info "Adding prometheus-community repository..."
        helm repo add "$HELM_REPO_PROMETHEUS" \
            "https://prometheus-community.github.io/helm-charts"
        helm repo update "$HELM_REPO_PROMETHEUS"
    fi
    log_success "prometheus-community repository ready"

    # Add grafana repo
    if helm repo list | grep -q "$HELM_REPO_GRAFANA"; then
        log_info "Updating existing grafana repository..."
        helm repo update "$HELM_REPO_GRAFANA"
    else
        log_info "Adding grafana repository..."
        helm repo add "$HELM_REPO_GRAFANA" \
            "https://grafana.github.io/helm-charts"
        helm repo update "$HELM_REPO_GRAFANA"
    fi
    log_success "grafana repository ready"

    # Update all repos
    log_info "Updating all Helm repositories..."
    helm repo update
    log_success "Helm repositories updated"
}

# Deploy Prometheus with custom values
deploy_prometheus() {
    log_info "Deploying Prometheus stack with Helm chart..."

    # Check if release already exists
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log_warning "Release '$RELEASE_NAME' already exists, upgrading..."
        helm upgrade "$RELEASE_NAME" "$HELM_CHART" \
            --version "$PROMETHEUS_VERSION" \
            --namespace "$NAMESPACE" \
            --values "${SCRIPT_DIR}/prometheus/values.yaml" \
            --timeout "$TIMEOUT" \
            --wait \
            --debug 2>&1 | head -20
    else
        log_info "Installing new release '$RELEASE_NAME'..."
        helm install "$RELEASE_NAME" "$HELM_CHART" \
            --version "$PROMETHEUS_VERSION" \
            --namespace "$NAMESPACE" \
            --values "${SCRIPT_DIR}/prometheus/values.yaml" \
            --timeout "$TIMEOUT" \
            --wait \
            --debug 2>&1 | head -20
    fi

    log_success "Prometheus stack deployment initiated"
}

# Apply Prometheus configuration
apply_prometheus_config() {
    log_info "Applying Prometheus configuration..."

    # Apply ConfigMap
    kubectl apply -f "${SCRIPT_DIR}/prometheus/configmap.yaml"
    log_success "Prometheus ConfigMap applied"

    # Apply ServiceMonitors
    kubectl apply -f "${SCRIPT_DIR}/prometheus/servicemonitor.yaml"
    log_success "ServiceMonitors applied"
}

# Deploy Grafana dashboards
deploy_grafana_dashboards() {
    log_info "Deploying Grafana dashboards..."

    # Apply datasource configuration
    kubectl apply -f "${SCRIPT_DIR}/grafana/datasources.yaml"
    log_success "Grafana datasources applied"

    # Create ConfigMap for dashboards
    log_info "Creating dashboard ConfigMaps..."

    kubectl create configmap grafana-dashboard-nest-overview \
        --from-file="${SCRIPT_DIR}/grafana/dashboards/nest-overview.json" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | \
        kubectl apply -f -

    kubectl label configmap grafana-dashboard-nest-overview \
        grafana_dashboard=1 \
        --namespace="$NAMESPACE" \
        --overwrite &> /dev/null

    kubectl create configmap grafana-dashboard-nest-resources \
        --from-file="${SCRIPT_DIR}/grafana/dashboards/nest-resources.json" \
        --namespace="$NAMESPACE" \
        --dry-run=client -o yaml | \
        kubectl apply -f -

    kubectl label configmap grafana-dashboard-nest-resources \
        grafana_dashboard=1 \
        --namespace="$NAMESPACE" \
        --overwrite &> /dev/null

    log_success "Grafana dashboards deployed"
}

# Apply AlertManager configuration
deploy_alertmanager() {
    log_info "Deploying AlertManager configuration..."

    kubectl apply -f "${SCRIPT_DIR}/alertmanager/config.yaml"
    log_success "AlertManager configuration applied"
}

# Deploy rsyslog
deploy_rsyslog() {
    log_info "Deploying rsyslog stack..."

    # Create storage class if it doesn't exist
    if ! kubectl get storageclass fast-ssd &> /dev/null; then
        log_warning "StorageClass 'fast-ssd' not found, creating standard storage class..."
        cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/no-provisioner
allowVolumeExpansion: true
EOF
    fi

    # Apply ConfigMaps
    kubectl apply -f "${SCRIPT_DIR}/rsyslog/configmap.yaml"
    log_success "rsyslog ConfigMaps applied"

    # Apply services
    kubectl apply -f "${SCRIPT_DIR}/rsyslog/service.yaml"
    log_success "rsyslog services applied"

    # Apply deployment
    kubectl apply -f "${SCRIPT_DIR}/rsyslog/deployment.yaml"
    log_success "rsyslog deployment applied"
}

# Wait for deployments
wait_for_deployments() {
    log_info "Waiting for deployments to be ready..."

    # Wait for Prometheus
    log_info "Waiting for Prometheus to be ready (timeout: 5m)..."
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=prometheus \
        -n "$NAMESPACE" \
        --timeout=5m 2>/dev/null || log_warning "Prometheus not ready within timeout"

    # Wait for Grafana
    log_info "Waiting for Grafana to be ready (timeout: 5m)..."
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=grafana \
        -n "$NAMESPACE" \
        --timeout=5m 2>/dev/null || log_warning "Grafana not ready within timeout"

    # Wait for AlertManager
    log_info "Waiting for AlertManager to be ready (timeout: 5m)..."
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=alertmanager \
        -n "$NAMESPACE" \
        --timeout=5m 2>/dev/null || log_warning "AlertManager not ready within timeout"

    # Wait for rsyslog
    log_info "Waiting for rsyslog to be ready (timeout: 3m)..."
    kubectl wait --for=condition=ready pod \
        -l app=rsyslog \
        -n "$NAMESPACE" \
        --timeout=3m 2>/dev/null || log_warning "rsyslog not ready within timeout"

    log_success "Deployment checks completed"
}

# Verify deployments
verify_deployments() {
    log_info "Verifying deployments..."

    echo ""
    log_info "=== Deployment Status ==="
    kubectl get deployments -n "$NAMESPACE" -o wide

    echo ""
    log_info "=== Pod Status ==="
    kubectl get pods -n "$NAMESPACE" -o wide

    echo ""
    log_info "=== Services ==="
    kubectl get svc -n "$NAMESPACE" -o wide

    echo ""
    log_info "=== StatefulSets ==="
    kubectl get statefulsets -n "$NAMESPACE" -o wide

    # Check pod health
    log_info "=== Pod Health Check ==="
    FAILED_PODS=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running,status.phase!=Succeeded -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    if [ -z "$FAILED_PODS" ]; then
        log_success "All pods are running"
    else
        log_warning "Some pods are not in Running state: $FAILED_PODS"
    fi
}

# Display access information
display_access_info() {
    echo ""
    log_info "=== Monitoring Stack Deployment Complete ==="
    echo ""

    log_info "Access Information:"
    echo "  Namespace: $NAMESPACE"
    echo ""

    # Prometheus
    echo "  Prometheus:"
    echo "    URL: http://localhost:9090"
    echo "    Port-forward: kubectl port-forward -n $NAMESPACE svc/kube-prometheus-stack-prometheus 9090:9090"
    echo ""

    # Grafana
    echo "  Grafana:"
    echo "    URL: http://localhost:3000"
    echo "    Default credentials: admin / admin"
    echo "    Port-forward: kubectl port-forward -n $NAMESPACE svc/kube-prometheus-stack-grafana 3000:80"
    echo ""

    # AlertManager
    echo "  AlertManager:"
    echo "    URL: http://localhost:9093"
    echo "    Port-forward: kubectl port-forward -n $NAMESPACE svc/kube-prometheus-stack-alertmanager 9093:9093"
    echo ""

    # rsyslog
    echo "  rsyslog:"
    echo "    UDP: localhost:514"
    echo "    TCP: localhost:514"
    echo "    Port-forward UDP: kubectl port-forward -n $NAMESPACE svc/rsyslog 514:514 --address=0.0.0.0"
    echo ""

    log_info "Useful commands:"
    echo "  View logs: kubectl logs -n $NAMESPACE -l app=prometheus -f"
    echo "  Check status: kubectl get all -n $NAMESPACE"
    echo "  Edit values: helm get values $RELEASE_NAME -n $NAMESPACE"
    echo "  Upgrade: helm upgrade $RELEASE_NAME $HELM_CHART -n $NAMESPACE -f prometheus/values.yaml"
    echo ""
}

# Cleanup function
cleanup_on_exit() {
    log_info "Deployment script completed"
}

# Main execution
main() {
    log_info "Starting NEST monitoring stack deployment..."
    echo ""

    trap cleanup_on_exit EXIT

    # Execute deployment steps
    check_prerequisites
    echo ""

    create_namespace
    echo ""

    add_helm_repos
    echo ""

    deploy_prometheus
    echo ""

    apply_prometheus_config
    echo ""

    deploy_grafana_dashboards
    echo ""

    deploy_alertmanager
    echo ""

    deploy_rsyslog
    echo ""

    wait_for_deployments
    echo ""

    verify_deployments
    echo ""

    display_access_info

    log_success "Monitoring stack deployment completed successfully!"
}

# Run main function
main "$@"
