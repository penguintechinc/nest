#!/bin/bash
# Nest Kubernetes Deployment Script
# Usage: ./deploy.sh [environment] [action] [--method {kubectl|kustomize}]
# Environments: dev, staging, prod
# Actions: apply (default), delete, validate
# Methods: kubectl (default), kustomize

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${1:-dev}
ACTION=${2:-apply}
METHOD=${3:-kubectl}
MANIFEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse --method flag if provided
if [[ $3 == --method ]]; then
  METHOD=${4:-kubectl}
elif [[ $4 == --method ]]; then
  METHOD=${5:-kubectl}
fi

# Convert environment shorthand to namespace
case $ENVIRONMENT in
  dev) NAMESPACE="nest-dev" ;;
  staging) NAMESPACE="nest-staging" ;;
  prod) NAMESPACE="nest-prod" ;;
  *)
    echo -e "${RED}Error: Unknown environment '$ENVIRONMENT'${NC}"
    echo "Valid options: dev, staging, prod"
    exit 1
    ;;
esac

# Functions
print_header() {
  echo -e "${GREEN}===========================================${NC}"
  echo -e "${GREEN}$1${NC}"
  echo -e "${GREEN}===========================================${NC}"
}

print_step() {
  echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

check_prerequisites() {
  print_header "Checking Prerequisites"

  # Check kubectl
  if ! command -v kubectl &> /dev/null; then
    print_error "kubectl not found. Please install kubectl."
    exit 1
  fi
  print_success "kubectl found"

  # Check cluster connection
  if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
  fi
  print_success "Kubernetes cluster accessible"

  # Check if namespace exists (for non-apply actions)
  if [ "$ACTION" != "apply" ]; then
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
      print_error "Namespace $NAMESPACE does not exist"
      exit 1
    fi
    print_success "Namespace $NAMESPACE exists"
  fi
}

validate_manifests() {
  print_header "Validating Manifests"

  if [ "$METHOD" = "kustomize" ]; then
    print_step "Validating with Kustomize..."
    if kubectl apply -k "$MANIFEST_DIR/overlays/$ENVIRONMENT" --dry-run=client -o yaml > /dev/null 2>&1; then
      print_success "Kustomize validation successful"
    else
      print_error "Invalid Kustomize configuration"
      exit 1
    fi
  else
    local manifests=(
      "00-namespace.yaml"
      "10-configmap.yaml"
      "11-secrets.yaml"
      "20-postgres-statefulset.yaml"
      "21-postgres-service.yaml"
      "30-redis-deployment.yaml"
      "31-redis-service.yaml"
      "40-app-deployment.yaml"
      "41-app-service.yaml"
      "50-ingress.yaml"
      "60-servicemonitor.yaml"
    )

    for manifest in "${manifests[@]}"; do
      if [ ! -f "$MANIFEST_DIR/$manifest" ]; then
        print_error "Manifest not found: $manifest"
        exit 1
      fi

      if kubectl apply -f "$MANIFEST_DIR/$manifest" --dry-run=client -o yaml > /dev/null 2>&1; then
        print_success "Validated: $manifest"
      else
        print_error "Invalid manifest: $manifest"
        exit 1
      fi
    done
  fi
}

apply_manifests() {
  print_header "Deploying to $NAMESPACE"

  if [ "$METHOD" = "kustomize" ]; then
    print_step "Applying Kustomize overlay: $ENVIRONMENT"
    kubectl apply -k "$MANIFEST_DIR/overlays/$ENVIRONMENT"
    print_success "Kustomize deployment applied to $NAMESPACE"
  else
    print_step "Creating namespaces..."
    kubectl apply -f "$MANIFEST_DIR/00-namespace.yaml"

    print_step "Applying configuration..."
    kubectl apply -f "$MANIFEST_DIR/10-configmap.yaml"
    kubectl apply -f "$MANIFEST_DIR/11-secrets.yaml"

    print_step "Deploying database..."
    kubectl apply -f "$MANIFEST_DIR/20-postgres-statefulset.yaml"
    kubectl apply -f "$MANIFEST_DIR/21-postgres-service.yaml"

    print_step "Deploying cache..."
    kubectl apply -f "$MANIFEST_DIR/30-redis-deployment.yaml"
    kubectl apply -f "$MANIFEST_DIR/31-redis-service.yaml"

    print_step "Deploying application..."
    kubectl apply -f "$MANIFEST_DIR/40-app-deployment.yaml"
    kubectl apply -f "$MANIFEST_DIR/41-app-service.yaml"

    print_step "Configuring ingress..."
    kubectl apply -f "$MANIFEST_DIR/50-ingress.yaml"

    print_step "Setting up monitoring..."
    kubectl apply -f "$MANIFEST_DIR/60-servicemonitor.yaml"

    print_success "All manifests applied to $NAMESPACE"
  fi
}

delete_manifests() {
  print_header "Removing deployment from $NAMESPACE"

  if [ "$NAMESPACE" == "nest-prod" ]; then
    echo -e "${RED}WARNING: You are about to delete the PRODUCTION namespace!${NC}"
    read -p "Type 'yes' to confirm: " confirm
    if [ "$confirm" != "yes" ]; then
      print_error "Deletion cancelled"
      exit 1
    fi
  fi

  if [ "$METHOD" = "kustomize" ]; then
    print_step "Removing Kustomize deployment: $ENVIRONMENT"
    kubectl delete -k "$MANIFEST_DIR/overlays/$ENVIRONMENT" --ignore-not-found
    print_success "Kustomize deployment removed from $NAMESPACE"
  else
    print_step "Removing ingress..."
    kubectl delete -f "$MANIFEST_DIR/50-ingress.yaml" --ignore-not-found

    print_step "Removing monitoring..."
    kubectl delete -f "$MANIFEST_DIR/60-servicemonitor.yaml" --ignore-not-found

    print_step "Removing application..."
    kubectl delete -f "$MANIFEST_DIR/41-app-service.yaml" --ignore-not-found
    kubectl delete -f "$MANIFEST_DIR/40-app-deployment.yaml" --ignore-not-found

    print_step "Removing cache..."
    kubectl delete -f "$MANIFEST_DIR/31-redis-service.yaml" --ignore-not-found
    kubectl delete -f "$MANIFEST_DIR/30-redis-deployment.yaml" --ignore-not-found

    print_step "Removing database..."
    kubectl delete -f "$MANIFEST_DIR/21-postgres-service.yaml" --ignore-not-found
    kubectl delete -f "$MANIFEST_DIR/20-postgres-statefulset.yaml" --ignore-not-found

    print_step "Removing configuration..."
    kubectl delete -f "$MANIFEST_DIR/11-secrets.yaml" --ignore-not-found
    kubectl delete -f "$MANIFEST_DIR/10-configmap.yaml" --ignore-not-found

    print_step "Removing namespace..."
    kubectl delete -f "$MANIFEST_DIR/00-namespace.yaml" --ignore-not-found

    print_success "All resources removed from $NAMESPACE"
  fi
}

wait_for_rollout() {
  print_header "Waiting for deployment to be ready"

  print_step "Waiting for nest-app deployment..."
  if kubectl rollout status deployment/nest-app -n $NAMESPACE --timeout=5m; then
    print_success "nest-app deployment is ready"
  else
    print_error "nest-app deployment failed to become ready"
    exit 1
  fi

  print_step "Waiting for postgres statefulset..."
  if kubectl rollout status statefulset/postgres -n $NAMESPACE --timeout=5m; then
    print_success "postgres statefulset is ready"
  else
    print_error "postgres statefulset failed to become ready"
    exit 1
  fi
}

show_status() {
  print_header "Deployment Status for $NAMESPACE"

  echo "Pods:"
  kubectl get pods -n $NAMESPACE -o wide

  echo -e "\nServices:"
  kubectl get services -n $NAMESPACE

  echo -e "\nStatefulSets:"
  kubectl get statefulsets -n $NAMESPACE

  echo -e "\nDeployments:"
  kubectl get deployments -n $NAMESPACE

  echo -e "\nPersistentVolumeClaims:"
  kubectl get pvc -n $NAMESPACE

  echo -e "\nIngress:"
  kubectl get ingress -n $NAMESPACE
}

# Main
case $ACTION in
  apply)
    check_prerequisites
    validate_manifests
    apply_manifests
    wait_for_rollout
    show_status
    print_header "Deployment Complete!"
    echo -e "Access your cluster at: ${GREEN}http://localhost:8080${NC} (port-forward)"
    echo -e "Or configure your domain in the ingress manifest"
    ;;
  delete)
    check_prerequisites
    delete_manifests
    print_success "Cleanup complete"
    ;;
  validate)
    check_prerequisites
    validate_manifests
    print_success "All manifests are valid"
    ;;
  status)
    check_prerequisites
    show_status
    ;;
  *)
    echo "Usage: $0 [environment] [action] [--method {kubectl|kustomize}]"
    echo ""
    echo "Environments:"
    echo "  dev         Development environment (default)"
    echo "  staging     Staging environment"
    echo "  prod        Production environment"
    echo ""
    echo "Actions:"
    echo "  apply       Deploy or update resources (default)"
    echo "  delete      Remove resources"
    echo "  validate    Validate manifests only"
    echo "  status      Show deployment status"
    echo ""
    echo "Methods:"
    echo "  kubectl     Direct kubectl apply (default)"
    echo "  kustomize   Use Kustomize overlays"
    echo ""
    echo "Examples:"
    echo "  $0 dev apply"
    echo "  $0 staging validate --method kustomize"
    echo "  $0 prod delete --method kubectl"
    echo "  $0 dev apply --method kustomize"
    exit 1
    ;;
esac
