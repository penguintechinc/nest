# Pre-Commit Checklist

**CRITICAL: This checklist MUST be followed before every commit.**

## Automated Pre-Commit Script

**Run the automated pre-commit script to execute all checks:**

```bash
./scripts/pre-commit/pre-commit.sh
```

This script will:
1. Run all checks in the correct order
2. Log output to `/tmp/pre-commit-nest-<epoch>.log`
3. Provide a summary of pass/fail status
4. Echo the log file location for review

**Individual check scripts** (run separately if needed):
- `./scripts/pre-commit/check-go.sh` - Go linting, security, build
- `./scripts/pre-commit/check-python.sh` - Python linting & security (for utilities)
- `./scripts/pre-commit/check-node.sh` - Node.js/React linting (if WebUI enabled)
- `./scripts/pre-commit/check-security.sh` - All security scans
- `./scripts/pre-commit/check-secrets.sh` - Secret detection
- `./scripts/pre-commit/check-docker.sh` - Docker build & validation
- `./scripts/pre-commit/check-tests.sh` - Unit tests

## Required Steps (In Order)

Before committing, run in this order (or use `./scripts/pre-commit/pre-commit.sh`):

### Foundation Checks
- [ ] **Go Linters**: `golangci-lint run ./...`
- [ ] **Security scans**: `gosec ./apps/...` (Go), `bandit -r ./scripts` (Python utilities)
- [ ] **No secrets**: Verify no credentials, API keys, or tokens in code

### Build & Integration Verification
- [ ] **Build & Run**: Verify code compiles and containers start successfully
  - `go build ./apps/api`
  - `docker-compose build go-api`
  - `docker-compose up -d && docker-compose logs`
- [ ] **Smoke tests** (mandatory, <2 min): `make smoke-test`
  - All containers build without errors
  - All containers start and remain healthy
  - All API health endpoints respond with 200 status
  - Go API endpoints functional
  - See: [Testing Documentation - Smoke Tests](TESTING.md#smoke-tests)

### Feature Testing & Documentation
- [ ] **Mock data** (for testing features): Ensure 3-4 test items per feature via `make seed-mock-data`
  - Populate development database with realistic test data
  - Needed for feature validation and documentation
  - See: [Testing Documentation - Mock Data Scripts](TESTING.md#mock-data-scripts)

### Comprehensive Testing
- [ ] **Unit tests**: `go test ./apps/...` and `pytest ./scripts/tests/`
  - Network isolated, mocked dependencies
  - Must pass before committing
- [ ] **Integration tests**: Component interaction verification
  - Tests with real database and service communication
  - See: [Testing Documentation - Integration Tests](TESTING.md#integration-tests)

### Finalization
- [ ] **Version updates**: Update `.version` if releasing new version
- [ ] **Documentation**: Update docs if adding/changing workflows
- [ ] **Docker builds**: Verify Dockerfile uses debian-slim base (no alpine)
- [ ] **Cross-architecture**: (Optional) Test alternate architecture with QEMU
  - `docker buildx build --platform linux/arm64 .` (if on amd64)
  - `docker buildx build --platform linux/amd64 .` (if on arm64)
  - See: [Testing Documentation - Cross-Architecture Testing](TESTING.md#cross-architecture-testing)

## Language-Specific Commands

### Go (Primary Language for Nest)

```bash
# Linting with golangci-lint (must install: golangci-lint install)
golangci-lint run ./apps/...
golangci-lint run ./libs/...

# Security scanning
gosec ./apps/...
gosec ./libs/...

# Format checking
gofmt -l .
goimports -l .

# Build & Run
go build -v ./apps/api
go run ./apps/api &                    # Verify it starts (then kill)

# Tests
go test ./apps/...
go test -race ./apps/...               # Race condition detection
go test -cover ./apps/...              # Coverage report
```

### Python (Utilities & Scripts)

```bash
# Linting
flake8 scripts/
black --check scripts/
isort --check scripts/
mypy scripts/

# Security
bandit -r scripts/
safety check

# Build & Run
python -m py_compile scripts/*.py      # Syntax check
pip install -r scripts/requirements.txt  # Dependencies
python scripts/seed-mock-data.py &     # Verify it starts (then kill)

# Tests
pytest scripts/tests/
```

### Node.js / JavaScript / TypeScript / ReactJS (if WebUI enabled)

```bash
# Linting
npm run lint
# or
npx eslint .

# Security (REQUIRED)
npm audit                          # Check for vulnerabilities
npm audit fix                      # Auto-fix if possible

# Build & Run
npm run build                      # Compile/bundle
npm start &                        # Verify it starts (then kill)

# Tests
npm test
```

### Docker / Containers

```bash
# Lint Dockerfiles
hadolint Dockerfile
hadolint apps/*/Dockerfile

# Verify base image (debian-slim, NOT alpine)
grep -E "^FROM.*slim" Dockerfile
grep -E "^FROM.*slim" apps/*/Dockerfile

# Build & Run
docker build -t nest-api:test apps/api/    # Build image
docker run -d --name test-container nest-api:test  # Start container
docker logs test-container                 # Check for errors
docker stop test-container && docker rm test-container  # Cleanup

# Docker Compose
docker-compose build                # Build all services
docker-compose up -d                # Start all services
docker-compose logs                 # Check for errors
docker-compose down                 # Cleanup
```

## Commit Rules

- **NEVER commit automatically** unless explicitly requested by the user
- **NEVER push to remote repositories** under any circumstances
- **ONLY commit when explicitly asked** - never assume commit permission
- **Wait for approval** before running `git commit`

## Security Scanning Requirements

### Before Every Commit
- **Run security audits on all modified packages**:
  - **Go packages**: Run `gosec ./apps/...` on modified Go services
  - **Node.js packages**: Run `npm audit` on modified Node.js services
  - **Python packages**: Run `bandit -r ./scripts` on modified Python utilities
- **Do NOT commit if security vulnerabilities are found** - fix all issues first
- **Document vulnerability fixes** in commit message if applicable

### Vulnerability Response
1. Identify affected packages and severity
2. Update to patched versions immediately
3. Test updated dependencies thoroughly
4. Document security fixes in commit messages
5. Verify no new vulnerabilities introduced

## API Testing Requirements

Before committing changes to Go API services:

- **Create and run API testing scripts** for each modified API service
- **Testing scope**: All new endpoints and modified functionality
- **Test files location**: `tests/api/` directory with service-specific subdirectories
  - `tests/api/go-api/` - Go API server tests
  - `tests/integration/` - Cross-service integration tests
- **Run before commit**: Each test script should be executable and pass completely
- **Test coverage**: Health checks, routing, CRUD operations, error cases, network scenarios

## Networking-Specific Testing (Nest)

For Nest's networking-focused features:

- [ ] **Network interface tests**: Validate interface detection and configuration
- [ ] **Routing tests**: Verify routing table management and manipulation
- [ ] **Packet handling tests**: If using XDP/AF_XDP, verify packet processing
- [ ] **Protocol compliance tests**: Ensure RFC compliance for networking protocols
- [ ] **Performance benchmarks**: Validate throughput and latency requirements
- [ ] **Cross-platform tests**: Test on both amd64 and arm64 if targeting both

## Mock Data Requirements

### Prerequisites
Before capturing data samples or doing feature testing:

```bash
make dev                   # Start all services
make seed-mock-data       # Populate with 3-4 test items per feature
```

### What to Mock
For networking features, create realistic mock data:

```bash
# Example: Routes, interfaces, connections
cat > scripts/mock-data/seed-networking.py << 'EOF'
from dal import DAL

def seed_networking():
    db = DAL('postgresql://...')

    # Mock network interfaces
    interfaces = [
        {"name": "eth0", "ip": "192.168.1.100", "status": "up"},
        {"name": "eth1", "ip": "10.0.0.100", "status": "up"},
        {"name": "lo", "ip": "127.0.0.1", "status": "up"},
    ]

    # Mock routing entries
    routes = [
        {"destination": "0.0.0.0/0", "gateway": "192.168.1.1", "metric": 1000},
        {"destination": "10.0.0.0/8", "gateway": "192.168.1.254", "metric": 100},
    ]

    for iface in interfaces:
        db.interfaces.insert(**iface)
    for route in routes:
        db.routes.insert(**route)

    print(f"✓ Seeded {len(interfaces)} interfaces and {len(routes)} routes")
EOF

# Run the mock data script
python scripts/mock-data/seed-networking.py
```

---

## Commit Message Format

Follow conventional commits for clear, semantic commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build, CI/CD, dependency updates

**Examples**:
```
feat(routing): add dynamic route management

fix(packet-handler): resolve buffer overflow in XDP module

docs(development): update local setup guide

perf(networking): optimize packet processing in AF_XDP
```

---

## Troubleshooting Pre-Commit Checks

### Go Linting Errors

**Common issues**:
- Unused imports: `goimports -w .`
- Formatting: `gofmt -w .`
- Simplification: Run `golangci-lint run --fix`

**Exclude specific checks**:
```bash
# Run with skip pattern
golangci-lint run --skip-dirs vendor,generated
```

### Security Vulnerabilities

**Fix known vulnerabilities**:
```bash
# Update Go modules
go get -u all
go mod tidy

# Update npm packages
npm audit fix
npm audit fix --force  # Use with caution

# Update Python packages
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### Test Failures

**Debug test failures**:
```bash
# Run with verbose output
go test -v ./apps/api
pytest -v scripts/tests/

# Run specific test
go test -run TestName ./apps/api
pytest scripts/tests/test_specific.py::test_name

# Run with race detection
go test -race ./apps/api
```

### Docker Build Failures

**Debug Docker issues**:
```bash
# Build with verbose output
docker build --verbose -t nest-api:test apps/api/

# Check layers
docker history nest-api:test

# Run container with interactive shell
docker run -it nest-api:test /bin/bash
```

---

## Related Documentation

- **Development**: [Development Guide](DEVELOPMENT.md)
  - Local setup and running services
  - Development workflow
  - Common development tasks

- **Testing**: [Testing Documentation](TESTING.md)
  - Smoke tests
  - Unit and integration tests
  - Performance testing
  - Cross-architecture testing

- **Standards**: [Development Standards](STANDARDS.md)
  - Code style and conventions
  - Architecture patterns
  - Database standards

- **Workflows**: [CI/CD Workflows](WORKFLOWS.md)
  - Automated testing pipelines
  - Build and deployment workflows
  - Release processes

---

**Last Updated**: 2026-01-06
**Maintained by**: Penguin Tech Inc
**Project**: Nest Networking Platform
