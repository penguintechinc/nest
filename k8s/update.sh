#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults
ENV="${ENV:-dev}"
COMPONENT="${COMPONENT:-nest}"
NAMESPACE="nest-${ENV}"
TIMEOUT="${TIMEOUT:-300}"
MAX_SURGE="${MAX_SURGE:-1}"
MAX_UNAVAILABLE="${MAX_UNAVAILABLE:-0}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --env ENV              Environment: dev, staging, prod (default: dev)
    --component COMP       Component to update: nest, management, storage (default: nest)
    --image IMAGE          Docker image to deploy (e.g., myrepo/nest:v1.2.3)
    --timeout SECS         Rollout timeout in seconds (default: 300)
    --max-surge NUM        Max surge during rolling update (default: 1)
    --max-unavailable NUM  Max unavailable replicas (default: 0)
    --rollback             Rollback to previous version
    --history              Show rollout history
    -h, --help             Show this help message

Examples:
    $0 --component nest --image myrepo/nest:v1.2.3
    $0 --env prod --component nest --image myrepo/nest:v2.0.0
    $0 --component nest --rollback
    $0 --component nest --history
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

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
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
}

check_deployment_exists() {
    local deployment="$1"

    if ! kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
        log_error "Deployment not found: $deployment"
        exit 1
    fi
}

update_image() {
    local deployment="$1"
    local image="$2"

    log_info "Updating deployment: $deployment"
    log_info "New image: $image"

    # Patch the deployment with new image
    kubectl set image deployment/"$deployment" \
        "nest=$image" \
        -n "$NAMESPACE" \
        --record \
        2>/dev/null || {
        # Try with wildcard container name if specific one fails
        kubectl set image deployment/"$deployment" \
            "*=$image" \
            -n "$NAMESPACE" \
            --record
    }

    log_info "Waiting for rollout to complete (timeout: ${TIMEOUT}s)..."

    if kubectl rollout status deployment/"$deployment" \
        -n "$NAMESPACE" \
        --timeout="${TIMEOUT}s"; then
        log_info "Rollout successful"
    else
        log_error "Rollout failed or timed out"
        return 1
    fi
}

wait_for_ready() {
    local deployment="$1"
    local max_attempts=$((TIMEOUT / 5))
    local attempt=0

    log_info "Verifying all pods are healthy..."

    while [[ $attempt -lt $max_attempts ]]; do
        local ready=$(kubectl get deployment "$deployment" -n "$NAMESPACE" \
            -o jsonpath='{.status.conditions[?(@.type=="Available")].status}')

        if [[ "$ready" == "True" ]]; then
            local pods=$(kubectl get pods -n "$NAMESPACE" \
                -l app="$deployment" \
                -o jsonpath='{.items[*].metadata.name}')

            log_info "Ready pods:"
            for pod in $pods; do
                local status=$(kubectl get pod "$pod" -n "$NAMESPACE" \
                    -o jsonpath='{.status.phase}')
                log_info "  - $pod: $status"
            done

            return 0
        fi

        ((attempt++))
        sleep 5
    done

    return 1
}

show_rollout_history() {
    local deployment="$1"

    log_info "Rollout history for: $deployment"
    kubectl rollout history deployment/"$deployment" -n "$NAMESPACE"
}

rollback_deployment() {
    local deployment="$1"

    log_warn "Rolling back deployment: $deployment"

    if kubectl rollout undo deployment/"$deployment" -n "$NAMESPACE"; then
        log_info "Rollback initiated, waiting for completion..."

        if kubectl rollout status deployment/"$deployment" \
            -n "$NAMESPACE" \
            --timeout="${TIMEOUT}s"; then
            log_info "Rollback successful"
        else
            log_error "Rollback failed or timed out"
            return 1
        fi
    else
        log_error "Failed to initiate rollback"
        return 1
    fi
}

main() {
    local image=""
    local action="update" # update, rollback, or history

    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ENV="$2"
                NAMESPACE="nest-${ENV}"
                shift 2
                ;;
            --component)
                COMPONENT="$2"
                shift 2
                ;;
            --image)
                image="$2"
                shift 2
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --max-surge)
                MAX_SURGE="$2"
                shift 2
                ;;
            --max-unavailable)
                MAX_UNAVAILABLE="$2"
                shift 2
                ;;
            --rollback)
                action="rollback"
                shift
                ;;
            --history)
                action="history"
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

    log_info "====== Nest Kubernetes Rolling Update ======"
    log_info "Environment: $ENV"
    log_info "Namespace: $NAMESPACE"
    log_info "Component: $COMPONENT"
    log_info "Action: $action"

    check_cluster_connection
    check_deployment_exists "$COMPONENT"

    case "$action" in
        update)
            if [[ -z "$image" ]]; then
                log_error "Image is required for update action"
                usage
            fi
            update_image "$COMPONENT" "$image" || exit 1
            wait_for_ready "$COMPONENT" || exit 1
            ;;
        rollback)
            rollback_deployment "$COMPONENT" || exit 1
            wait_for_ready "$COMPONENT" || exit 1
            ;;
        history)
            show_rollout_history "$COMPONENT"
            ;;
    esac

    log_info "====== Update Complete ======"
}

main "$@"
