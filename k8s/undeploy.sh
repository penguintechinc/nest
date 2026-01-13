#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults
ENV="${ENV:-dev}"
NAMESPACE="nest-${ENV}"
FORCE="${FORCE:-false}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --env ENV              Environment: dev, staging, prod (default: dev)
    --force               Skip confirmation prompt
    --keep-namespace      Don't delete the namespace
    -h, --help            Show this help message

Examples:
    $0 --env dev
    $0 --env prod --force
EOF
    exit 0
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
    local prompt="$1"
    local response

    read -p "$prompt (yes/no): " response
    if [[ "$response" == "yes" ]]; then
        return 0
    else
        return 1
    fi
}

check_cluster_connection() {
    log_info "Validating cluster connection..."

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace not found: $NAMESPACE"
        exit 1
    fi

    log_info "Connected to cluster and namespace exists"
}

undeploy_application() {
    log_info "Removing application resources..."

    # Delete Helm release if it exists
    if helm list -n "$NAMESPACE" | grep -q "nest"; then
        log_info "Deleting Helm release: nest"
        helm delete nest -n "$NAMESPACE"
    fi

    # Delete kubectl-managed resources
    if [[ -f "${PROJECT_ROOT}/k8s/manifests/application.yaml" ]]; then
        log_info "Deleting application manifests..."
        kubectl delete -f "${PROJECT_ROOT}/k8s/manifests/application.yaml" -n "$NAMESPACE" --ignore-not-found=true
    fi

    log_info "Application removal complete"
}

undeploy_management() {
    log_info "Removing management cluster resources..."

    if helm list -n "$NAMESPACE" | grep -q "management"; then
        log_info "Deleting Helm release: management"
        helm delete management -n "$NAMESPACE"
    fi

    if [[ -f "${PROJECT_ROOT}/k8s/manifests/management.yaml" ]]; then
        log_info "Deleting management manifests..."
        kubectl delete -f "${PROJECT_ROOT}/k8s/manifests/management.yaml" -n "$NAMESPACE" --ignore-not-found=true
    fi

    log_info "Management removal complete"
}

undeploy_storage() {
    log_info "Removing storage resources..."

    if helm list -n "$NAMESPACE" | grep -q "storage"; then
        log_info "Deleting Helm release: storage"
        helm delete storage -n "$NAMESPACE"
    fi

    if [[ -f "${PROJECT_ROOT}/k8s/manifests/storage.yaml" ]]; then
        log_info "Deleting storage manifests..."
        kubectl delete -f "${PROJECT_ROOT}/k8s/manifests/storage.yaml" -n "$NAMESPACE" --ignore-not-found=true
    fi

    log_info "Storage removal complete"
}

cleanup_namespace() {
    if [[ "${KEEP_NAMESPACE:-false}" == "true" ]]; then
        log_warn "Keeping namespace: $NAMESPACE"
        return
    fi

    log_info "Deleting namespace: $NAMESPACE"
    kubectl delete namespace "$NAMESPACE" --ignore-not-found=true

    # Wait for namespace deletion
    local max_attempts=30
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
            log_info "Namespace deleted successfully"
            return
        fi
        ((attempt++))
        sleep 1
    done

    log_warn "Namespace deletion timed out, manual cleanup may be needed"
}

main() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ENV="$2"
                shift 2
                ;;
            --force)
                FORCE="true"
                shift
                ;;
            --keep-namespace)
                KEEP_NAMESPACE="true"
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done

    log_warn "====== Nest Kubernetes Undeployment ======"
    log_warn "Environment: $ENV"
    log_warn "Namespace: $NAMESPACE"

    check_cluster_connection

    if [[ "$FORCE" != "true" ]]; then
        if ! confirm "This will delete all Nest resources from $NAMESPACE. Continue?"; then
            log_info "Undeployment cancelled"
            exit 0
        fi
    fi

    undeploy_application
    sleep 2
    undeploy_management
    sleep 2
    undeploy_storage
    cleanup_namespace

    log_warn "====== Undeployment Complete ======"
}

main "$@"
