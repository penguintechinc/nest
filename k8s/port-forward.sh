#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Defaults
ENV="${ENV:-dev}"
SERVICE="${SERVICE:-}"
COMPONENT="${COMPONENT:-}"
NAMESPACE="nest-${ENV}"
LOCAL_PORT="${LOCAL_PORT:-}"
REMOTE_PORT="${REMOTE_PORT:-}"

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
    --service SERVICE      Kubernetes service name
    --component COMP       Component name (alternative to --service)
    --local-port PORT      Local port to bind to (default: auto)
    --remote-port PORT     Remote port on service (default: 80 or 8080)
    --pod POD              Forward to specific pod instead of service
    --pod-port PORT        Pod port to forward to
    --list                 List available services
    -h, --help             Show this help message

Examples:
    $0 --service nest --local-port 8080 --remote-port 8080
    $0 --component management --remote-port 9090
    $0 --pod nest-deployment-abc123-xyz --pod-port 8080 --local-port 8080
    $0 --list
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

list_services() {
    log_info "Available services in namespace: $NAMESPACE"
    kubectl get svc -n "$NAMESPACE" -o wide
    echo ""
    log_info "Available pods in namespace: $NAMESPACE"
    kubectl get pods -n "$NAMESPACE" -o wide
}

get_service_port() {
    local service="$1"
    local port=$(kubectl get svc "$service" -n "$NAMESPACE" \
        -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)

    if [[ -z "$port" ]]; then
        # Try to get targetPort if port doesn't exist
        port=$(kubectl get svc "$service" -n "$NAMESPACE" \
            -o jsonpath='{.spec.ports[0].targetPort}' 2>/dev/null)
    fi

    echo "$port"
}

get_service_by_component() {
    local component="$1"
    # Service names typically match component names
    local service=$(kubectl get svc -n "$NAMESPACE" \
        -o jsonpath='{.items[?(@.metadata.labels.app=="'$component'")].metadata.name}' 2>/dev/null | awk '{print $1}')

    if [[ -z "$service" ]]; then
        # Fall back to component name as service name
        service="$component"
    fi

    echo "$service"
}

get_pod_by_component() {
    local component="$1"
    local pod=$(kubectl get pods -n "$NAMESPACE" \
        -l app="$component" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [[ -z "$pod" ]]; then
        log_error "No pods found for component: $component"
        exit 1
    fi

    echo "$pod"
}

find_available_local_port() {
    local start_port=8000

    for port in $(seq $start_port $((start_port + 100))); do
        if ! nc -z localhost $port &>/dev/null 2>&1; then
            echo $port
            return
        fi
    done

    log_error "Could not find available local port"
    exit 1
}

forward_service() {
    local service="$1"
    local local_port="$2"
    local remote_port="$3"

    # Verify service exists
    if ! kubectl get svc "$service" -n "$NAMESPACE" &>/dev/null; then
        log_error "Service not found: $service"
        exit 1
    fi

    # Auto-detect remote port if not provided
    if [[ -z "$remote_port" ]]; then
        remote_port=$(get_service_port "$service")
        if [[ -z "$remote_port" ]]; then
            remote_port=8080
        fi
    fi

    # Auto-detect local port if not provided
    if [[ -z "$local_port" ]]; then
        local_port=$(find_available_local_port)
    fi

    log_info "====== Port Forward (Service) ======"
    log_info "Service: $service"
    log_info "Remote port: $remote_port"
    log_info "Local port: $local_port"
    log_warn "Press Ctrl+C to stop port forwarding"
    log_info "Access at: http://localhost:$local_port"
    log_info ""

    trap "log_info 'Port forwarding stopped'" EXIT

    kubectl port-forward -n "$NAMESPACE" "svc/$service" "$local_port:$remote_port"
}

forward_pod() {
    local pod="$1"
    local local_port="$2"
    local pod_port="$3"

    # Verify pod exists
    if ! kubectl get pod "$pod" -n "$NAMESPACE" &>/dev/null; then
        log_error "Pod not found: $pod"
        exit 1
    fi

    if [[ -z "$pod_port" ]]; then
        log_error "Pod port is required (--pod-port)"
        exit 1
    fi

    # Auto-detect local port if not provided
    if [[ -z "$local_port" ]]; then
        local_port=$(find_available_local_port)
    fi

    log_info "====== Port Forward (Pod) ======"
    log_info "Pod: $pod"
    log_info "Pod port: $pod_port"
    log_info "Local port: $local_port"
    log_warn "Press Ctrl+C to stop port forwarding"
    log_info "Access at: http://localhost:$local_port"
    log_info ""

    trap "log_info 'Port forwarding stopped'" EXIT

    kubectl port-forward -n "$NAMESPACE" "pod/$pod" "$local_port:$pod_port"
}

main() {
    local pod=""
    local pod_port=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ENV="$2"
                NAMESPACE="nest-${ENV}"
                shift 2
                ;;
            --service)
                SERVICE="$2"
                shift 2
                ;;
            --component)
                COMPONENT="$2"
                shift 2
                ;;
            --local-port)
                LOCAL_PORT="$2"
                shift 2
                ;;
            --remote-port)
                REMOTE_PORT="$2"
                shift 2
                ;;
            --pod)
                pod="$2"
                shift 2
                ;;
            --pod-port)
                pod_port="$2"
                shift 2
                ;;
            --list)
                check_cluster_connection
                list_services
                exit 0
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

    # Handle pod port forwarding
    if [[ ! -z "$pod" ]]; then
        forward_pod "$pod" "$LOCAL_PORT" "$pod_port"
    else
        # Handle service port forwarding
        if [[ -z "$SERVICE" && ! -z "$COMPONENT" ]]; then
            SERVICE=$(get_service_by_component "$COMPONENT")
        fi

        if [[ -z "$SERVICE" ]]; then
            log_error "Service or component must be specified"
            usage
        fi

        forward_service "$SERVICE" "$LOCAL_PORT" "$REMOTE_PORT"
    fi
}

main "$@"
