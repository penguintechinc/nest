#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults
ENV="${ENV:-dev}"
METHOD="${METHOD:-helm}"
NAMESPACE="nest-${ENV}"
DRY_RUN="${DRY_RUN:-false}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --env ENV              Environment: dev, staging, prod (default: dev)
    --method METHOD        Deployment method: helm or kubectl (default: helm)
    --dry-run             Show what would be deployed without applying
    --skip-storage        Skip storage deployment
    --skip-management     Skip management cluster deployment
    --skip-app            Skip application deployment
    -h, --help            Show this help message

Examples:
    $0 --env dev --method helm
    $0 --env prod --method kubectl --dry-run
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

validate_env() {
    case "$ENV" in
        dev|staging|prod)
            log_info "Deploying to environment: $ENV"
            ;;
        *)
            log_error "Invalid environment: $ENV. Must be dev, staging, or prod."
            exit 1
            ;;
    esac
}

validate_method() {
    case "$METHOD" in
        helm|kubectl)
            log_info "Using deployment method: $METHOD"
            ;;
        *)
            log_error "Invalid method: $METHOD. Must be helm or kubectl."
            exit 1
            ;;
    esac
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi

    # Check helm for helm deployments
    if [[ "$METHOD" == "helm" ]]; then
        if ! command -v helm &> /dev/null; then
            log_error "helm is not installed"
            exit 1
        fi
        local helm_version=$(helm version --short 2>&1 | head -n1 | cut -d+ -f1)
        if [[ "$helm_version" < "3.0" ]]; then
            log_error "Helm 3.0+ required, found: $helm_version"
            exit 1
        fi
        log_info "Helm version: $helm_version"
    fi

    log_info "kubectl version: $(kubectl version --client 2>&1 | grep -oP 'v\d+\.\d+\.\d+' | head -1)"
}

validate_cluster_connection() {
    log_info "Validating cluster connection..."

    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    local cluster_info=$(kubectl cluster-info | head -n1)
    log_info "Connected to: $cluster_info"

    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
    fi
}

deploy_storage() {
    if [[ "${SKIP_STORAGE:-false}" == "true" ]]; then
        log_warn "Skipping storage deployment"
        return
    fi

    log_info "Deploying storage layer..."

    if [[ "$METHOD" == "helm" ]]; then
        # Add Helm repos for storage
        helm repo add stable https://charts.helm.sh/stable || true
        helm repo update

        # Deploy storage (example: local storage provisioner)
        local cmd="helm upgrade --install storage stable/nfs-server-provisioner \
            --namespace $NAMESPACE \
            --values ${PROJECT_ROOT}/k8s/helm/storage-values.yaml"

        if [[ "$DRY_RUN" == "true" ]]; then
            $cmd --dry-run --debug
        else
            $cmd
        fi
    else
        # kubectl method
        if [[ -f "${PROJECT_ROOT}/k8s/manifests/storage.yaml" ]]; then
            local cmd="kubectl apply -f ${PROJECT_ROOT}/k8s/manifests/storage.yaml"
            if [[ "$DRY_RUN" == "true" ]]; then
                $cmd --dry-run=client
            else
                $cmd
            fi
        else
            log_warn "Storage manifest not found, skipping"
        fi
    fi

    log_info "Storage deployment complete"
}

deploy_management() {
    if [[ "${SKIP_MANAGEMENT:-false}" == "true" ]]; then
        log_warn "Skipping management cluster deployment"
        return
    fi

    log_info "Deploying management cluster..."

    if [[ "$METHOD" == "helm" ]]; then
        if [[ ! -d "${PROJECT_ROOT}/k8s/helm/management" ]]; then
            log_warn "Management Helm chart not found, skipping"
            return
        fi

        local cmd="helm upgrade --install management ${PROJECT_ROOT}/k8s/helm/management \
            --namespace $NAMESPACE \
            --set environment=$ENV"

        if [[ "$DRY_RUN" == "true" ]]; then
            $cmd --dry-run --debug
        else
            $cmd
        fi
    else
        if [[ -f "${PROJECT_ROOT}/k8s/manifests/management.yaml" ]]; then
            local cmd="kubectl apply -f ${PROJECT_ROOT}/k8s/manifests/management.yaml"
            if [[ "$DRY_RUN" == "true" ]]; then
                $cmd --dry-run=client
            else
                $cmd
            fi
        else
            log_warn "Management manifest not found, skipping"
        fi
    fi

    log_info "Management deployment complete"
}

deploy_application() {
    if [[ "${SKIP_APP:-false}" == "true" ]]; then
        log_warn "Skipping application deployment"
        return
    fi

    log_info "Deploying application..."

    if [[ "$METHOD" == "helm" ]]; then
        if [[ ! -d "${PROJECT_ROOT}/k8s/helm/nest" ]]; then
            log_warn "Application Helm chart not found, skipping"
            return
        fi

        local values_file="${PROJECT_ROOT}/k8s/helm/nest/values-${ENV}.yaml"
        if [[ ! -f "$values_file" ]]; then
            values_file="${PROJECT_ROOT}/k8s/helm/nest/values.yaml"
        fi

        local cmd="helm upgrade --install nest ${PROJECT_ROOT}/k8s/helm/nest \
            --namespace $NAMESPACE \
            --values $values_file"

        if [[ "$DRY_RUN" == "true" ]]; then
            $cmd --dry-run --debug
        else
            $cmd
        fi
    else
        if [[ -f "${PROJECT_ROOT}/k8s/manifests/application.yaml" ]]; then
            local cmd="kubectl apply -f ${PROJECT_ROOT}/k8s/manifests/application.yaml"
            if [[ "$DRY_RUN" == "true" ]]; then
                $cmd --dry-run=client
            else
                $cmd
            fi
        else
            log_warn "Application manifest not found, skipping"
        fi
    fi

    log_info "Application deployment complete"
}

verify_deployment() {
    log_info "Verifying deployment..."

    # Wait for deployments to be ready
    local max_attempts=60
    local attempt=0

    while [[ $attempt -lt $max_attempts ]]; do
        local ready=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].status.conditions[?(@.type=="Available")].status}' 2>/dev/null | tr ' ' '\n' | grep -c "True" || echo 0)
        local total=$(kubectl get deployments -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)

        if [[ $total -eq 0 ]]; then
            log_warn "No deployments found yet"
            ((attempt++))
            sleep 2
            continue
        fi

        if [[ $ready -eq $total ]]; then
            log_info "All deployments are ready ($ready/$total)"
            break
        fi

        log_info "Waiting for deployments to be ready ($ready/$total)"
        ((attempt++))
        sleep 2
    done

    if [[ $attempt -ge $max_attempts ]]; then
        log_warn "Deployment verification timed out"
    fi

    # Show deployment status
    kubectl get deployments -n "$NAMESPACE"
    kubectl get pods -n "$NAMESPACE"
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ENV="$2"
                shift 2
                ;;
            --method)
                METHOD="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --skip-storage)
                SKIP_STORAGE="true"
                shift
                ;;
            --skip-management)
                SKIP_MANAGEMENT="true"
                shift
                ;;
            --skip-app)
                SKIP_APP="true"
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

    log_info "====== Nest Kubernetes Deployment ======"
    log_info "Environment: $ENV"
    log_info "Method: $METHOD"
    log_info "Namespace: $NAMESPACE"
    [[ "$DRY_RUN" == "true" ]] && log_warn "DRY RUN MODE"

    validate_env
    validate_method
    check_prerequisites
    validate_cluster_connection

    if [[ "$DRY_RUN" != "true" ]]; then
        log_warn "Starting deployment in 5 seconds... (Ctrl+C to cancel)"
        sleep 5
    fi

    deploy_storage
    deploy_management
    deploy_application
    verify_deployment

    log_info "====== Deployment Complete ======"
}

main "$@"
