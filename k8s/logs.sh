#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults
ENV="${ENV:-dev}"
COMPONENT="${COMPONENT:-}"
NAMESPACE="nest-${ENV}"
TAIL="${TAIL:-100}"
FOLLOW="${FOLLOW:-false}"
TIMESTAMPS="${TIMESTAMPS:-true}"

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
    --component COMP       Component name (e.g., nest, management, storage)
    --pod POD              Specific pod name to tail
    --tail NUM             Number of lines to tail (default: 100)
    --follow               Follow logs (like tail -f)
    --no-timestamps        Hide timestamps in logs
    --container NAME       Specific container within pod
    --previous             Show logs from previous container instance
    --all-pods             Show logs from all pods in namespace
    -h, --help             Show this help message

Examples:
    $0 --component nest --tail 50
    $0 --pod nest-deployment-abc123-xyz --follow
    $0 --env prod --component management --follow
    $0 --all-pods
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
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace not found: $NAMESPACE"
        exit 1
    fi
}

get_pod_by_component() {
    local component="$1"
    local pods=$(kubectl get pods -n "$NAMESPACE" \
        -l app="$component" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -z "$pods" ]]; then
        log_error "No pods found for component: $component"
        exit 1
    fi

    echo "$pods"
}

get_all_pods() {
    kubectl get pods -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n'
}

tail_pod_logs() {
    local pod="$1"
    local container="${2:-}"
    local flags=""

    # Build kubectl flags
    if [[ "$TIMESTAMPS" != "true" ]]; then
        flags="$flags --timestamps=false"
    fi

    flags="$flags --tail=$TAIL"

    if [[ "$FOLLOW" == "true" ]]; then
        flags="$flags -f"
    fi

    if [[ ! -z "$container" ]]; then
        flags="$flags -c $container"
    fi

    if [[ "${PREVIOUS:-false}" == "true" ]]; then
        flags="$flags --previous"
    fi

    log_info "Tailing logs from pod: $pod"
    kubectl logs -n "$NAMESPACE" $flags "$pod"
}

tail_all_pod_logs() {
    local pods=$(get_all_pods)

    if [[ -z "$pods" ]]; then
        log_error "No pods found in namespace: $NAMESPACE"
        exit 1
    fi

    log_info "Tailing logs from all pods in namespace: $NAMESPACE"

    local flags=""
    if [[ "$TIMESTAMPS" != "true" ]]; then
        flags="$flags --timestamps=false"
    fi

    flags="$flags --tail=$TAIL"

    if [[ "$FOLLOW" == "true" ]]; then
        flags="$flags -f"
    fi

    # Use kubectl logs with multiple pods (requires kubectl 1.23+)
    kubectl logs -n "$NAMESPACE" $flags $(echo "$pods" | tr '\n' ' ')
}

list_pods() {
    log_info "Available pods in namespace: $NAMESPACE"
    kubectl get pods -n "$NAMESPACE" -o wide
}

main() {
    local pod=""
    local container=""

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
            --pod)
                pod="$2"
                shift 2
                ;;
            --tail)
                TAIL="$2"
                shift 2
                ;;
            --follow)
                FOLLOW="true"
                shift
                ;;
            --no-timestamps)
                TIMESTAMPS="false"
                shift
                ;;
            --container)
                container="$2"
                shift 2
                ;;
            --previous)
                PREVIOUS="true"
                shift
                ;;
            --all-pods)
                ALL_PODS="true"
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

    check_cluster_connection

    # Handle different log modes
    if [[ "${ALL_PODS:-false}" == "true" ]]; then
        tail_all_pod_logs
    elif [[ ! -z "$pod" ]]; then
        tail_pod_logs "$pod" "$container"
    elif [[ ! -z "$COMPONENT" ]]; then
        local target_pod=$(get_pod_by_component "$COMPONENT")
        tail_pod_logs "$target_pod" "$container"
    else
        log_warn "No pod or component specified. Available pods:"
        list_pods
        exit 0
    fi
}

main "$@"
