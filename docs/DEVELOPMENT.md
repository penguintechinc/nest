# Local Development Guide

Complete guide to setting up a local development environment for Nest, running the platform locally, and following the development workflow including testing and pre-commit checks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Starting Development Environment](#starting-development-environment)
4. [Development Workflow](#development-workflow)
5. [Common Tasks](#common-tasks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **macOS 12+**, **Linux (Ubuntu 20.04+)**, or **Windows 10+ with WSL2**
- **Docker Desktop** 4.0+ (or Docker Engine 20.10+)
- **Docker Compose** 2.0+
- **Git** 2.30+
- **Go** 1.23.2+ (mandatory for Nest)
- **Python** 3.13+ (for Python services and scripts)
- **Node.js** 18+ (for WebUI and tooling)

### Optional Tools

- **Docker Buildx** (for multi-architecture builds)
- **Helm** (for Kubernetes deployments)
- **kubectl** (for Kubernetes clusters)
- **golangci-lint** (Go linting)
- **gosec** (Go security scanning)

### Installation

**macOS (Homebrew)**:
```bash
brew install docker docker-compose git golang python node
brew install --cask docker
brew install golangci-lint gosec
```

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git golang-1.23 python3.13 nodejs
sudo usermod -aG docker $USER  # Allow docker without sudo
newgrp docker                   # Activate group change
GO_VERSION=1.23.2 && wget https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz && sudo tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz
```

**Verify Installation**:
```bash
docker --version          # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
git --version
go version                 # Go 1.23.2+
python3 --version         # Python 3.13+
node --version            # Node.js 18+
golangci-lint --version   # Optional
gosec --version           # Optional
```

---

## Initial Setup

### Clone Repository

```bash
git clone <repository-url>
cd Nest
```

### Install Dependencies

```bash
# Install all project dependencies
make setup
```

This runs:
1. Go module setup (go mod download)
2. Python environment setup (venv, requirements for utilities)
3. Node.js dependency installation (npm install)
4. Pre-commit hooks installation
5. Database initialization

### Environment Configuration

Copy and customize environment files:

```bash
# Copy example environment file
cp .env.example .env
```

**Key Environment Variables**:
```bash
# Database
DB_TYPE=postgres            # postgres, mysql, sqlite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nest_dev
DB_USER=postgres
DB_PASSWORD=postgres

# Go Services
GO_ENV=development
GO_DEBUG=1
LOG_LEVEL=debug

# License (Development - all features available)
RELEASE_MODE=false
LICENSE_KEY=not-required-in-dev

# Port Configuration
GO_API_PORT=8000
WEBUI_PORT=3000
REDIS_PORT=6379
POSTGRES_PORT=5432

# Networking (Nest-specific)
ENABLE_XDP=false            # XDP kernel bypass (if supported)
ENABLE_AF_XDP=false         # AF_XDP socket acceleration
PACKET_BUFFER_SIZE=65536
```

### Database Initialization

```bash
# Create database and run migrations
make db-init

# Seed with mock data (3-4 items per entity)
make seed-mock-data

# Verify database connection
make db-health
```

---

## Starting Development Environment

### Quick Start (All Services)

```bash
# Start all services in one command
make dev

# This runs:
# - PostgreSQL database
# - Redis cache
# - Go API services
# - Node.js WebUI (if included)

# Access the services:
# Go API:      http://localhost:8000
# WebUI:       http://localhost:3000 (if enabled)
# Adminer:     http://localhost:8080 (database UI)
```

### Individual Service Management

**Start specific services**:
```bash
# Start only Go services
docker-compose up -d go-api

# Start database and cache
docker-compose up -d postgres redis

# Start without detaching (see logs)
docker-compose up go-api
```

**View service logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f go-api

# Last 100 lines, follow new entries
docker-compose logs -f --tail=100 webui
```

**Stop services**:
```bash
# Stop all services (keep data)
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Restart services
docker-compose restart

# Rebuild and restart (apply code changes)
docker-compose down && docker-compose up -d --build
```

### Development Docker Compose Files

- **`docker-compose.yml`**: Full production-like setup with all services
- Environment-specific configurations via `.env` file

---

## Development Workflow

### 1. Start Development Environment

```bash
make dev        # Start all services
make seed-data  # Populate with test data
```

### 2. Make Code Changes

Edit Go files in your favorite editor. Services require restart:

- **Go**: Requires restart (`docker-compose restart go-api` or rebuild with `--build`)
- **Python utilities**: Reload on file save or restart container
- **Node.js (WebUI)**: Hot reload in dev mode

### 3. Rebuild Services After Code Changes

```bash
# Rebuild and restart all services
docker-compose down && docker-compose up -d --build

# Or rebuild specific service
docker-compose up -d --build go-api

# Important: docker restart or docker-compose restart will NOT apply code changes
# Always use --build flag to rebuild images with new code
```

### 4. Verify Changes

```bash
# Quick smoke tests
make smoke-test

# Run linters (Go)
make lint

# Run unit tests
cd apps/api && go test ./...

# Run security scans
golangci-lint run ./apps/...
gosec ./apps/...
```

### 5. Populate Mock Data for Feature Testing

After implementing a new networking feature:

```bash
# Create mock data script (e.g., for new "Routes" feature)
cat > scripts/mock-data/seed-routes.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dal import DAL

def seed_routes():
    db = DAL('postgresql://user:password@localhost/nest_dev')

    routes = [
        {"destination": "10.0.0.0/8", "gateway": "192.168.1.1", "metric": 100},
        {"destination": "172.16.0.0/12", "gateway": "192.168.1.1", "metric": 100},
        {"destination": "192.168.0.0/16", "gateway": "192.168.1.254", "metric": 50},
        {"destination": "0.0.0.0/0", "gateway": "192.168.1.1", "metric": 1000},
    ]

    for route in routes:
        db.routes.insert(**route)

    print(f"✓ Seeded {len(routes)} routes")

if __name__ == "__main__":
    seed_routes()
EOF

# Run the mock data script
python scripts/mock-data/seed-routes.py

# Add to seed-all.py orchestrator
echo "from seed_routes import seed_routes; seed_routes()" >> scripts/mock-data/seed-all.py
```

📚 **Complete Mock Data Guide**: [Testing Documentation - Mock Data Scripts](TESTING.md#mock-data-scripts)

### 6. Run Pre-Commit Checklist

Before committing, run the comprehensive pre-commit script:

```bash
./scripts/pre-commit/pre-commit.sh
```

**Steps**:
1. ✅ Go linters (golangci-lint, gosec)
2. ✅ Python linters (flake8, black, isort, bandit)
3. ✅ Security scans (gosec, bandit)
4. ✅ Secret detection (no API keys, passwords, tokens)
5. ✅ Build & Run (build all containers, verify runtime)
6. ✅ Smoke tests (mandatory, <2 min)
7. ✅ Unit tests (isolated component testing)
8. ✅ Version update & Docker standards

**Troubleshooting Pre-Commit**:

See [Pre-Commit Documentation](PRE_COMMIT.md) for detailed guidance on:
- Fixing linting errors
- Resolving security vulnerabilities
- Excluding files from checks
- Bypassing specific checks (with justification)

### 7. Testing & Validation

Comprehensive testing guide:

📚 **Complete Testing Guide**: [Testing Documentation](TESTING.md)

**Quick Test Commands**:
```bash
# Smoke tests only (fast, <2 min)
make smoke-test

# Unit tests only
make test-unit

# Integration tests only (with Docker services)
make test-integration

# All tests
make test

# Specific test file
go test ./apps/api/handlers -v

# Cross-architecture testing (QEMU)
make test-multiarch
```

### 8. Create Pull Request

Once tests pass:

```bash
# Push branch
git push origin feature-branch-name

# Create PR via GitHub CLI
gh pr create --title "Brief feature description" \
  --body "Detailed description of changes"

# Or use web UI: https://github.com/penguintechinc/Nest/compare
```

### 9. Code Review & Merge

- Address review feedback
- Re-run tests if changes made
- Merge when approved

---

## Common Tasks

### Adding a Go Dependency

```bash
# Add dependency
cd apps/api
go get github.com/user/package@latest

# Update go.mod and go.sum
go mod tidy

# Rebuild API service
docker-compose up -d --build go-api

# Verify import works
docker-compose exec go-api go list -m all | grep package
```

### Adding a Python Utility Dependency

```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> scripts/requirements.txt

# Rebuild containers using python
docker-compose up -d --build

# Verify import works
docker-compose exec go-api python -c "import new_package"
```

### Adding a Node.js Dependency

```bash
# Add to WebUI package.json (if enabled)
cd webui && npm install new-package

# Rebuild WebUI container
docker-compose up -d --build webui

# Verify in running container
docker-compose exec webui npm list new-package
```

### Adding a New Environment Variable

```bash
# Add to .env
echo "NEW_VAR=value" >> .env

# Restart services to pick up new variable
docker-compose restart

# Verify it's set
docker-compose exec go-api printenv | grep NEW_VAR
```

### Debugging a Service

**View logs in real-time**:
```bash
docker-compose logs -f go-api
```

**Access container shell**:
```bash
# Go service
docker-compose exec go-api sh

# Python utilities
docker-compose exec go-api bash
```

**Execute commands in container**:
```bash
# Run Go test
docker-compose exec go-api go test ./...

# Check service health
docker-compose exec go-api curl http://localhost:8000/health
```

### Database Operations

**Connect to database**:
```bash
# PostgreSQL
docker-compose exec postgres psql -U postgres -d nest_dev

# View schema
\dt                    # PostgreSQL tables
SHOW TABLES;           # MySQL tables
```

**Reset database**:
```bash
# Full reset (deletes all data)
docker-compose down -v
make db-init
make seed-mock-data
```

**Run migrations**:
```bash
# Auto-migrate on startup
docker-compose restart go-api

# Or manually run migration
docker-compose exec go-api go run ./cmd/migrate
```

### Working with Git Branches

```bash
# Create feature branch
git checkout -b feature/new-feature-name

# Keep branch updated with main
git fetch origin
git rebase origin/main

# Clean commit history before PR
git rebase -i origin/main  # Interactive rebase

# Push branch
git push origin feature/new-feature-name
```

### Database Backups

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres nest_dev > backup.sql

# Restore from backup
docker-compose exec -T postgres psql -U postgres nest_dev < backup.sql
```

---

## Troubleshooting

### Services Won't Start

**Check if ports are already in use**:
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different ports in .env
GO_API_PORT=8001
```

**Docker daemon not running**:
```bash
# macOS
open /Applications/Docker.app

# Linux
sudo systemctl start docker

# Windows (Docker Desktop)
# Start Docker Desktop from Applications
```

### Database Connection Error

```bash
# Verify database container is running
docker-compose ps postgres

# Check database credentials in .env
cat .env | grep DB_

# Connect to database directly
docker-compose exec postgres psql -U postgres -d postgres

# View logs
docker-compose logs postgres
```

### Go API Won't Start

```bash
# Check logs
docker-compose logs go-api

# Verify module initialization
docker-compose exec go-api go mod tidy

# Reset and rebuild
docker-compose down
docker-compose up -d --build go-api
```

### Smoke Tests Failing

**Check which test failed**:
```bash
# Run individually
./tests/smoke/build/test-go-build.sh
./tests/smoke/api/test-go-health.sh
```

**Common issues**:
- Service not healthy (logs: `docker-compose logs <service>`)
- Port not exposed (check docker-compose.yml)
- API endpoint not implemented
- Missing environment variables

See [Testing Documentation - Smoke Tests](TESTING.md#smoke-tests) for detailed troubleshooting.

### Networking Issues in Containers

```bash
# Test connectivity between containers
docker-compose exec go-api ping postgres

# Test external connectivity
docker-compose exec go-api curl https://api.example.com

# Check DNS resolution
docker-compose exec go-api nslookup google.com

# View network configuration
docker network inspect nest_default
```

### Git Merge Conflicts

```bash
# View conflicts
git status

# Edit conflicted files (marked with <<<<, ====, >>>>)
# Remove conflict markers and keep desired code

# Mark as resolved
git add <resolved-file>

# Complete merge
git commit -m "Resolve merge conflicts"
```

### Slow Docker Builds

```bash
# Check Docker disk usage
docker system df

# Clean up unused images/containers
docker system prune

# Rebuild without cache (slow, but fresh)
docker-compose build --no-cache go-api
```

### QEMU Cross-Architecture Build Issues

**QEMU not available**:
```bash
# Install QEMU support
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

# Verify buildx setup
docker buildx ls
```

**Slow arm64 build with QEMU**:
```bash
# Expected: 2-5x slower with QEMU emulation
# Use only for final validation, not every iteration

# Build native architecture (fast)
docker buildx build --load .

# Build alternate with QEMU (slow)
docker buildx build --platform linux/arm64 .
```

See [Testing Documentation - Cross-Architecture Testing](TESTING.md#cross-architecture-testing) for complete details.

---

## Tips & Best Practices

### Hot Reload Development

For fastest iteration on Python/Node utilities:
```bash
# Start services once
docker-compose up -d

# Edit Python files → restart container to reload
# Edit JavaScript files → hot reload in dev mode
# Edit Go files → rebuild with --build
```

### Environment-Specific Configuration

```bash
# Development settings (auto-loaded)
.env              # Default development config
.env.local        # Local machine overrides (gitignored)

# Production settings (via secret management)
Kubernetes secrets
AWS Secrets Manager
HashiCorp Vault
```

### Networking Troubleshooting Checklist

For Nest's networking-specific issues:
```bash
# Check network interfaces
docker-compose exec go-api ip link show

# Monitor packet flow
docker-compose exec go-api tcpdump -i eth0

# Check routing tables
docker-compose exec go-api ip route show

# Test DNS resolution
docker-compose exec go-api nslookup example.com
```

### Performance Tips

```bash
# Use specific services to reduce memory usage
docker-compose up postgres go-api  # Skip WebUI if not needed

# Use lightweight testing
make smoke-test  # Instead of full test suite while developing

# Monitor resource usage
docker stats

# Rebuild in order of change frequency
Dockerfile: base → dependencies → code → entrypoint
```

---

## Related Documentation

- **Testing**: [Testing Documentation](TESTING.md)
  - Mock data scripts
  - Smoke tests
  - Unit/integration/E2E tests
  - Performance tests
  - Cross-architecture testing

- **Pre-Commit**: [Pre-Commit Checklist](PRE_COMMIT.md)
  - Linting requirements
  - Security scanning
  - Build verification
  - Test requirements

- **Standards**: [Development Standards](STANDARDS.md)
  - Architecture decisions
  - Code style
  - API conventions
  - Database patterns

- **Workflows**: [CI/CD Workflows](WORKFLOWS.md)
  - GitHub Actions pipelines
  - Build automation
  - Test automation
  - Release processes

---

**Last Updated**: 2026-01-06
**Maintained by**: Penguin Tech Inc
**Project**: Nest Networking Platform
