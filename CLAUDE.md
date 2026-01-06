# Nest - Claude Code Context

## Project Overview

Nest is a comprehensive networking and infrastructure platform built on enterprise-grade architecture and integrated licensing. It combines the Penguin Tech Inc template best practices with specialized networking capabilities and microservices architecture.

**Project Features:**
- Multi-language support (Go 1.23.x, Python 3.12/3.13, Node.js 18+)
- Specialized networking stack with performance optimization
- Enterprise security and licensing integration
- Comprehensive CI/CD pipeline
- Production-ready containerization
- Monitoring and observability
- Version management system
- PenguinTech License Server integration

## Technology Stack

### Languages & Frameworks

**Language Selection Criteria (Case-by-Case Basis):**
- **Python 3.13**: Default choice for most applications
  - Web applications and APIs
  - Business logic and data processing
  - Integration services and connectors
- **Go 1.23.x**: ONLY for high-traffic/performance-critical applications
  - Applications handling >10K requests/second
  - Network-intensive services
  - Low-latency requirements (<10ms)
  - CPU-bound operations requiring maximum throughput

**Python Stack:**
- **Python**: 3.13 for all applications (3.12+ minimum)
- **Web Framework**: Flask + Flask-Security-Too (mandatory)
- **Database**: SQLAlchemy for initialization, PyDAL for operations (mandatory)
- **Performance**: Dataclasses with slots, type hints, async/await required

**Frontend Stack:**
- **React**: ReactJS for all frontend applications
- **Node.js**: 18+ for build tooling and React development
- **JavaScript/TypeScript**: Modern ES2022+ standards

**Go Stack (When Required):**
- **Go**: 1.23.x (latest patch version)
- **Database**: Use DAL with PostgreSQL/MySQL cross-support (e.g., GORM, sqlx)
- Use only for traffic-intensive applications

### Infrastructure & DevOps
- **Containers**: Docker with multi-stage builds, Docker Compose
- **Orchestration**: Kubernetes with Helm charts
- **Configuration Management**: Ansible for infrastructure automation
- **CI/CD**: GitHub Actions with comprehensive pipelines
- **Monitoring**: Prometheus metrics, Grafana dashboards
- **Logging**: Structured logging with configurable levels

### Databases & Storage
- **Primary**: PostgreSQL (default, configurable via `DB_TYPE` environment variable)
- **Cache**: Redis/Valkey with optional TLS and authentication
- **Database Strategy (Hybrid Approach)**:
  - **SQLAlchemy**: Used for database **initialization only** (schema creation)
    - PyDAL has been struggling with database initialization
    - SQLAlchemy handles initial table creation reliably across all supported DBs
  - **PyDAL**: Used for **migrations and day-to-day operations** (mandatory)
    - All CRUD operations, queries, and schema migrations
    - Special support for MariaDB Galera cluster requirements
  - **Go**: GORM or sqlx (mandatory for cross-database support)
    - Must support PostgreSQL and MySQL/MariaDB
    - Stable, well-maintained library required
- **Migrations**: Automated schema management via PyDAL
- **MariaDB Galera Support**: Handle Galera-specific requirements (WSREP, auto-increment, transactions)

**Supported DB_TYPE Values** (Docker ENV):
```bash
DB_TYPE=postgres   # PostgreSQL (default)
DB_TYPE=mysql      # MySQL/MariaDB/Galera
DB_TYPE=sqlite     # SQLite (development/testing)
GALERA_MODE=true   # Enable MariaDB Galera cluster mode (optional)
```

**MariaDB Galera Cluster Requirements** (Mandatory when using Galera):
- **WSREP sync wait**: Set `wsrep_sync_wait=1` for read-your-writes consistency
- **Auto-increment**: Use `innodb_autoinc_lock_mode=2` (interleaved) for Galera compatibility
- **Transaction isolation**: Avoid `SERIALIZABLE`; use `READ-COMMITTED` or `REPEATABLE-READ`
- **Primary keys**: ALL tables MUST have explicit primary keys (Galera requirement)
- **MyISAM forbidden**: Use InnoDB only (MyISAM not replicated)
- **Large transactions**: Avoid transactions >1GB; chunk large batch operations
- **Connection handling**: Implement retry logic for `WSREP_NOT_READY` errors
- **DDL operations**: Schema changes lock entire cluster; schedule during maintenance windows

### Security & Authentication
- **Flask-Security-Too**: Mandatory for all Flask applications
  - Role-based access control (RBAC)
  - User authentication and session management
  - Password hashing with bcrypt
  - Email confirmation and password reset
  - Two-factor authentication (2FA)
- **TLS**: Enforce TLS 1.2 minimum, prefer TLS 1.3
- **HTTP3/QUIC**: Utilize UDP with TLS for high-performance connections where possible
- **Authentication**: JWT and MFA (standard), mTLS where applicable
- **SSO**: SAML/OAuth2 SSO as enterprise-only features
- **Secrets**: Environment variable management
- **Scanning**: Trivy vulnerability scanning, CodeQL analysis
- **Code Quality**: All code must pass CodeQL security analysis

## PenguinTech License Server Integration

All projects integrate with the centralized PenguinTech License Server at `https://license.penguintech.io` for feature gating and enterprise functionality.

**IMPORTANT: License enforcement is ONLY enabled when project is marked as release-ready**
- Development phase: All features available, no license checks
- Release phase: License validation required, feature gating active

**License Key Format**: `PENG-XXXX-XXXX-XXXX-XXXX-ABCD`

**Core Endpoints**:
- `POST /api/v2/validate` - Validate license
- `POST /api/v2/features` - Check feature entitlements
- `POST /api/v2/keepalive` - Report usage statistics

**Environment Variables**:
```bash
# License configuration
LICENSE_KEY=PENG-XXXX-XXXX-XXXX-XXXX-ABCD
LICENSE_SERVER_URL=https://license.penguintech.io
PRODUCT_NAME=your-product-identifier

# Release mode (enables license enforcement)
RELEASE_MODE=false  # Development (default)
RELEASE_MODE=true   # Production (explicitly set)
```

📚 **Detailed Documentation**: [License Server Integration Guide](docs/licensing/license-server-integration.md)

## WaddleAI Integration (Optional)

For projects requiring AI capabilities, integrate with WaddleAI located at `~/code/WaddleAI`.

**When to Use WaddleAI:**
- Natural language processing (NLP)
- Machine learning model inference
- AI-powered features and automation
- Intelligent data analysis
- Chatbots and conversational interfaces

**Integration Pattern:**
- WaddleAI runs as separate microservice container
- Communicate via REST API or gRPC
- Environment variable configuration for API endpoints
- License-gate AI features as enterprise functionality

📚 **WaddleAI Documentation**: See WaddleAI project at `~/code/WaddleAI` for integration details

## Project Structure

```
Nest/
├── .github/             # CI/CD pipelines and templates
│   └── workflows/       # GitHub Actions for each container
├── apps/                # Application services (networking stack)
├── app-skeleton/        # Application skeleton/templates
├── libs/                # Shared libraries
├── infrastructure/      # Infrastructure as code
├── scripts/             # Utility scripts
├── tests/               # Test suites (unit, integration, e2e, performance)
├── docs/                # Documentation
├── docker-compose.yml   # Production environment
├── docker-compose.dev.yml # Local development
├── Makefile             # Build automation
├── .version             # Version tracking
└── CLAUDE.md            # This file
```

### Three-Container Architecture

This template provides three base containers representing the core footprints:

| Container | Purpose | When to Use |
|-----------|---------|-------------|
| **flask-backend** | Standard APIs, auth, CRUD | <10K req/sec, business logic |
| **go-backend** | High-performance networking | >10K req/sec, <10ms latency |
| **webui** | Node.js + React frontend | All frontend applications |

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (optional)                               │
└─────────────────────────────────────────────────────────────────────────────┘
          │                        │                          │
┌─────────┴─────────┐   ┌─────────┴─────────┐   ┌────────────┴────────────┐
│  WebUI Container  │   │  Flask Backend    │   │    Go Backend           │
│  (Node.js/React)  │   │  (Flask/PyDAL)    │   │    (XDP/AF_XDP)         │
│                   │   │                   │   │                         │
│ - React SPA       │   │ - /api/v1/auth/*  │   │ - High-perf networking  │
│ - Proxies to APIs │   │ - /api/v1/users/* │   │ - XDP packet processing │
│ - Static assets   │   │ - /api/v1/hello   │   │ - AF_XDP zero-copy      │
│ - Port 3000       │   │ - Port 5000       │   │ - NUMA-aware memory     │
└───────────────────┘   └───────────────────┘   │ - Port 8080             │
                                 │              └─────────────────────────┘
                        ┌────────┴────────┐
                        │   PostgreSQL    │
                        └─────────────────┘
```

### Default Roles (WebUI)

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: user CRUD, settings, all features |
| **Maintainer** | Read/write access to resources, no user management |
| **Viewer** | Read-only access to resources |

## Shared Security Libraries (MANDATORY)

**ALL applications MUST use the shared libraries** for input validation, security, and cryptographic operations. These libraries provide consistent, secure implementations across Python, Go, and TypeScript.

### Library Overview

| Library | Package | Install Command |
|---------|---------|-----------------|
| **Python** | `py_libs` | `pip install -e "shared/py_libs[all]"` |
| **Go** | `go_libs` | `go get github.com/penguintechinc/project-template/shared/go_libs` |
| **TypeScript** | `@penguin/node_libs` | `npm install file:shared/node_libs` |

### Required Usage

**Input Validation** - ALL API endpoints MUST use shared validators:
```python
# Python (Flask) - MANDATORY for all user input
from py_libs.validation import chain, IsNotEmpty, IsEmail, IsLength

email_validator = chain(IsNotEmpty(), IsLength(3, 255), IsEmail())
result = email_validator(user_input)
if not result.is_valid:
    return {"error": result.error}, 400
```

**Security Middleware** - MANDATORY for all HTTP endpoints:
- Rate limiting (in-memory + Redis backends)
- Secure headers (CSP, HSTS, X-Frame-Options)
- CSRF protection
- Audit logging

**Cryptographic Operations** - MANDATORY for sensitive data:
- Password hashing: Argon2id (Python/Node.js), bcrypt (Go)
- Encryption: AES-256-GCM
- Token generation: Cryptographically secure random

📚 **Detailed Documentation**: [Shared Libraries README](shared/README.md)

## Kubernetes Deployment

All services are Kubernetes-ready with Helm charts and raw manifests in `k8s/`:

### Helm Charts (`k8s/helm/`)
```bash
# Deploy Flask backend to development namespace
helm install flask-backend k8s/helm/flask-backend \
  --namespace dev \
  --values k8s/helm/flask-backend/values-dev.yaml

# Deploy Go backend
helm install go-backend k8s/helm/go-backend --namespace dev

# Deploy WebUI
helm install webui k8s/helm/webui --namespace dev
```

### Raw Manifests (`k8s/manifests/`)
```bash
# Apply namespace and RBAC
kubectl apply -f k8s/manifests/namespace.yaml
kubectl apply -f k8s/manifests/rbac.yaml

# Deploy services
kubectl apply -f k8s/manifests/flask-backend/
kubectl apply -f k8s/manifests/go-backend/
kubectl apply -f k8s/manifests/webui/
```

### Kustomize Overlays (`k8s/kustomize/`)
```bash
# Deploy to development
kubectl apply -k k8s/kustomize/overlays/dev

# Deploy to staging
kubectl apply -k k8s/kustomize/overlays/staging

# Deploy to production
kubectl apply -k k8s/kustomize/overlays/prod
```

Each service deploys to its own namespace with proper RBAC, HPA, and resource limits.

📚 **Kubernetes Documentation**: [k8s/README.md](k8s/README.md)

## Version Management System

**Format**: `vMajor.Minor.Patch.build`
- **Major**: Breaking changes, API changes, removed features
- **Minor**: Significant new features and functionality additions
- **Patch**: Minor updates, bug fixes, security patches
- **Build**: Epoch64 timestamp of build time

**Update Commands**:
```bash
./scripts/version/update-version.sh          # Increment build timestamp
./scripts/version/update-version.sh patch    # Increment patch version
./scripts/version/update-version.sh minor    # Increment minor version
./scripts/version/update-version.sh major    # Increment major version
```

## Development Workflow

### Local Development Setup
```bash
git clone <repository-url>
cd Nest
make setup                    # Install dependencies
make dev                      # Start development environment
```

### Essential Commands
```bash
# Development
make dev                      # Start development services
make test                     # Run all tests
make lint                     # Run linting
make build                    # Build all services
make clean                    # Clean build artifacts

# Production
make docker-build             # Build containers
make docker-push              # Push to registry
make deploy-dev               # Deploy to development
make deploy-prod              # Deploy to production

# Testing
make test-unit               # Run unit tests
make test-integration        # Run integration tests
make test-e2e                # Run end-to-end tests

# License Management
make license-validate        # Validate license
make license-check-features  # Check available features
```

### Claude Code Model Strategy (Token-Smart Development)

**Opus Model (Planning & Orchestration Only)**:
- Opus MUST ONLY be used for planning, orchestrating multi-step tasks, and architectural decisions
- Opus MUST NEVER implement code directly - delegate implementation to task agents
- When planning tasks, Opus identifies scope, breaks work into steps, and launches appropriate agents
- Opus handles user communication, clarification questions, and final reviews

**Task Agent Model Selection**:
- **Haiku (Default)**: Use for straightforward implementation tasks AND ALL Docker CLI operations
  - Single-file changes, simple bug fixes, routine refactoring
  - Code generation for standard patterns
  - All Docker operations: builds, runs, compose, image management
  - Most general-purpose tasks (80%+ of work)
- **Sonnet (Complex Tasks Only)**: Reserve for genuinely complex tasks
  - Multi-file architectural changes requiring deep codebase understanding
  - Complex algorithm implementation or performance optimization
  - Tasks requiring sophisticated reasoning across multiple systems
- **Opus (Planning Only)**: Never for implementation - see above

**Post-Build Test Script Generation**:
- Once application builds successfully, Opus can create initial API and WebUI page/tab load test scripts
- These scripts are created once and stored for future use
- Prevents wasting tokens on redundant test script generation in subsequent development phases
- Test scripts should cover health checks, authentication, core workflows, and load scenarios

**Token Conservation Practices**:
- Batch related tasks where possible - let agents handle multiple similar changes in one execution
- Reuse test scripts and automation tools created in previous phases
- Avoid redundant explorations - document findings once, reference thereafter
- Keep task agents focused: clear, specific prompts yield better results than vague requests
- Verify build success locally before committing to prevent expensive troubleshooting cycles

## Critical Development Rules

### Development Philosophy: Safe, Stable, and Feature-Complete

**NEVER take shortcuts or the "easy route" - ALWAYS prioritize safety, stability, and feature completeness**

#### Core Principles
- **No Quick Fixes**: Resist quick workarounds or partial solutions
- **Complete Features**: Fully implemented with proper error handling and validation
- **Safety First**: Security, data integrity, and fault tolerance are non-negotiable
- **Stable Foundations**: Build on solid, tested components
- **Future-Proof Design**: Consider long-term maintainability and scalability
- **No Technical Debt**: Address issues properly the first time

#### Red Flags (Never Do These)
- ❌ Skipping input validation "just this once"
- ❌ Writing custom validators instead of using shared libraries (py_libs/go_libs/node_libs)
- ❌ Hardcoding credentials or configuration
- ❌ Ignoring error returns or exceptions
- ❌ Commenting out failing tests to make CI pass
- ❌ Deploying without proper testing
- ❌ Using deprecated or unmaintained dependencies
- ❌ Implementing partial features with "TODO" placeholders
- ❌ Bypassing security checks for convenience
- ❌ Assuming data is valid without verification
- ❌ Leaving debug code or backdoors in production

#### Quality Checklist Before Completion
- ✅ All error cases handled properly
- ✅ Unit tests cover all code paths
- ✅ Integration tests verify component interactions
- ✅ Security requirements fully implemented
- ✅ Performance meets acceptable standards
- ✅ Documentation complete and accurate
- ✅ Code review standards met
- ✅ No hardcoded secrets or credentials
- ✅ Logging and monitoring in place
- ✅ Build passes in containerized environment
- ✅ No security vulnerabilities in dependencies
- ✅ Edge cases and boundary conditions tested

### Git Workflow
- **NEVER commit automatically** unless explicitly requested by the user
- **NEVER push to remote repositories** under any circumstances
- **ONLY commit when explicitly asked** - never assume commit permission
- Always use feature branches for development
- Require pull request reviews for main branch
- Automated testing must pass before merge

**Before Every Commit - Security Scanning**:
- **Run security audits on all modified packages**:
  - **Go packages**: Run `gosec ./...` on modified Go services
  - **Node.js packages**: Run `npm audit` on modified Node.js services
  - **Python packages**: Run `bandit -r .` and `safety check` on modified Python services
- **Do NOT commit if security vulnerabilities are found** - fix all issues first
- **Document vulnerability fixes** in commit message if applicable

**Before Every Commit - API Testing**:
- **Create and run API testing scripts** for each modified container service
- **Testing scope**: All new endpoints and modified functionality
- **Test files location**: `tests/api/` directory with service-specific subdirectories
  - `tests/api/flask-backend/` - Flask backend API tests
  - `tests/api/go-backend/` - Go backend API tests
  - `tests/api/webui/` - WebUI container tests
- **Run before commit**: Each test script should be executable and pass completely
- **Test coverage**: Health checks, authentication, CRUD operations, error cases
- **Command pattern**: `cd services/<service-name> && npm run test:api` or equivalent

**Before Every Commit - Screenshots**:
- **Run screenshot tool to update UI screenshots in documentation**
  - Run `cd services/webui && npm run screenshots` to capture current UI state
  - This automatically removes old screenshots and captures fresh ones
  - Commit updated screenshots with relevant feature/documentation changes

### Local State Management (Crash Recovery)
- **ALWAYS maintain local .PLAN and .TODO files** for crash recovery
- **Keep .PLAN file updated** with current implementation plans and progress
- **Keep .TODO file updated** with task lists and completion status
- **Update these files in real-time** as work progresses
- **Add to .gitignore**: Both .PLAN and .TODO files must be in .gitignore
- **File format**: Use simple text format for easy recovery
- **Automatic recovery**: Upon restart, check for existing files to resume work

### Dependency Security Requirements
- **ALWAYS check for Dependabot alerts** before every commit
- **Monitor vulnerabilities via Socket.dev** for all dependencies
- **Mandatory security scanning** before any dependency changes
- **Fix all security alerts immediately** - no commits with outstanding vulnerabilities
- **Regular security audits**: `npm audit`, `go mod audit`, `safety check`

### Linting & Code Quality Requirements
- **ALL code must pass linting** before commit - no exceptions
- **Python**: flake8, black, isort, pytest, pytest-cov, mypy (type checking), bandit (security)
- **JavaScript/TypeScript**: ESLint, Prettier, TypeScript, Vitest, Testing Library
- **Go**: golangci-lint (includes staticcheck, gosec, etc.)
- **Ansible**: ansible-lint
- **Docker**: hadolint, trivy
- **YAML**: yamllint
- **Markdown**: markdownlint
- **Shell**: shellcheck
- **CodeQL**: All code must pass CodeQL security analysis
- **PEP Compliance**: Python code must follow PEP 8, PEP 257 (docstrings), PEP 484 (type hints)

### Build & Deployment Requirements
- **NEVER mark tasks as completed until successful build verification**
- All Go and Python builds MUST be executed within Docker containers
- Use containerized builds for local development and CI/CD pipelines
- Build failures must be resolved before task completion

### Documentation Standards
- **Markdown file locations** (STRICT):
  - `{PROJECT_ROOT}/README.md` - Project overview only
  - `{PROJECT_ROOT}/CLAUDE.md` - Claude Code context only
  - `{PROJECT_ROOT}/docs/` - ALL other markdown documentation
  - **NEVER nest markdown files in subdirectories** outside of `docs/`
- **README.md**: Keep as overview and pointer to comprehensive docs/ folder
- **docs/ folder**: Create comprehensive documentation for all aspects
- **RELEASE_NOTES.md**: Maintain in docs/ folder, prepend new version releases to top
- Update CLAUDE.md when adding significant context
- **Build status badges**: Always include in README.md
- **ASCII art**: Include catchy, project-appropriate ASCII art in README
- **Company homepage**: Point to www.penguintech.io
- **License**: All projects use Limited AGPL3 with preamble for fair use

### File Size Limits
- **Maximum file size**: 25,000 characters for ALL code and markdown files
- **Split large files**: Decompose into modules, libraries, or separate documents
- **CLAUDE.md exception**: Maximum 39,000 characters (only exception to 25K rule)
- **High-level approach**: CLAUDE.md contains high-level context and references detailed docs
- **Documentation strategy**: Create detailed documentation in `docs/` folder and link to them from CLAUDE.md
- **Keep focused**: Critical context, architectural decisions, and workflow instructions only
- **User approval required**: ALWAYS ask user permission before splitting CLAUDE.md files
- **Use Task Agents**: Utilize task agents (subagents) to be more expedient and efficient when making changes to large files, updating or reviewing multiple files, or performing complex multi-step operations
- **Avoid sed/cat**: Use sed and cat commands only when necessary; prefer dedicated Read/Edit/Write tools for file operations

## Development Standards

Comprehensive development standards are documented separately to keep this file concise.

📚 **Complete Standards Documentation**: [Development Standards](docs/STANDARDS.md)

### Quick Reference

**API Versioning**:
- ALL REST APIs MUST use versioning: `/api/v{major}/endpoint` format
- Semantic versioning for major versions only in URL
- Support current and previous versions (N-1) minimum
- Add deprecation headers to old versions
- Document migration paths for version changes

**Database Standards**:
- **Hybrid approach**: SQLAlchemy for init, PyDAL for day-to-day operations
- DB_TYPE environment variable: `postgres`, `mysql`, or `sqlite` only
- Thread-safe usage with thread-local connections
- Environment variable configuration for all database settings
- Connection pooling and retry logic required

**Protocol Support**:
- REST API, gRPC, HTTP/1.1, HTTP/2, HTTP/3 support
- Environment variables for protocol configuration
- Multi-protocol implementation required

**Performance Optimization (Python):**
- Dataclasses with slots mandatory (30-50% memory reduction)
- Type hints required for all Python code
- asyncio for I/O-bound operations
- threading for blocking I/O
- multiprocessing for CPU-bound operations
- Avoid premature optimization - profile first

**High-Performance Networking (Case-by-Case):**
- XDP (eXpress Data Path): Kernel-level packet processing
- AF_XDP: Zero-copy socket for user-space packet processing
- Use only for network-intensive applications requiring >100K packets/sec
- Evaluate Python vs Go based on traffic requirements

**Microservices Architecture**:
- Web UI, API, and Connector as **separate containers by default**
- Single responsibility per service
- API-first design
- Independent deployment and scaling
- Each service has its own Dockerfile and dependencies

**Docker Standards**:
- Multi-arch builds (amd64/arm64)
- Debian-slim base images
- Docker Compose for local development
- Minimal host port exposure

**Testing**:
- Unit tests: Network isolated, mocked dependencies
- Integration tests: Component interactions
- E2E tests: Critical workflows
- Performance tests: Scalability validation

**Security**:
- TLS 1.2+ required
- Input validation mandatory
- JWT, MFA, mTLS standard
- SSO as enterprise feature

## Application Architecture

**ALWAYS use microservices architecture** - decompose into specialized, independently deployable containers:

1. **Web UI Container**: ReactJS frontend (separate container, served via nginx)
2. **Application API Container**: Flask + Flask-Security-Too backend (separate container)
3. **Connector Container**: External system integration (separate container)

**Default Container Separation**: Web UI and API are ALWAYS separate containers by default. This provides:
- Independent scaling of frontend and backend
- Different resource allocation per service
- Separate deployment lifecycles
- Technology-specific optimization

**Benefits**:
- Independent scaling
- Technology diversity
- Team autonomy
- Resilience
- Continuous deployment

📚 **Detailed Architecture Patterns**: See [Development Standards - Microservices Architecture](docs/STANDARDS.md#microservices-architecture)

## Common Integration Patterns

### Flask + Flask-Security-Too + Hybrid Database (SQLAlchemy init + PyDAL ops)
```python
from flask import Flask
from flask_security import Security, auth_required
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Boolean, Text
from pydal import DAL, Field
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')

# Build connection string based on DB_TYPE
DB_TYPE = os.getenv('DB_TYPE', 'postgres')  # postgres, mysql, or sqlite
DB_URLS = {
    'postgres': f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    'mysql': f"mysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    'sqlite': f"sqlite:///{os.getenv('DB_PATH', 'app.db')}"
}

# ============ SQLAlchemy for DATABASE INITIALIZATION ONLY ============
def init_database():
    """Use SQLAlchemy for initial schema creation (PyDAL struggles with init)"""
    engine = create_engine(DB_URLS[DB_TYPE])
    metadata = MetaData()

    # Define tables for initialization
    Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('email', String(255), unique=True, nullable=False),
        Column('password', String(255)),
        Column('active', Boolean, default=True),
        Column('fs_uniquifier', String(255), unique=True))

    Table('roles', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(80), unique=True),
        Column('description', Text))

    metadata.create_all(engine)
    engine.dispose()

# ============ PyDAL for DAY-TO-DAY OPERATIONS ============
db = DAL(DB_URLS[DB_TYPE], pool_size=10, migrate=True)

# Define tables in PyDAL for migrations and operations
db.define_table('users',
    Field('email', 'string', unique=True),
    Field('password', 'string'),
    Field('active', 'boolean', default=True),
    Field('fs_uniquifier', 'string', unique=True))

db.define_table('roles',
    Field('name', 'string', unique=True),
    Field('description', 'text'))

# Flask-Security-Too setup with PyDAL
from flask_security import PyDALUserDatastore
user_datastore = PyDALUserDatastore(db, db.users, db.roles)
security = Security(app, user_datastore)

@app.route('/api/v1/protected')
@auth_required()
def protected_resource():
    return {'message': 'This is a protected endpoint'}

@app.route('/healthz')
def health():
    return {'status': 'healthy'}, 200
```

### ReactJS Frontend Integration
```javascript
// API client for Flask backend
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Protected component example
import React, { useEffect, useState } from 'react';

function ProtectedComponent() {
  const [data, setData] = useState(null);

  useEffect(() => {
    apiClient.get('/api/v1/protected')
      .then(response => setData(response.data))
      .catch(error => console.error('Error:', error));
  }, []);

  return <div>{data?.message}</div>;
}
```

### License-Gated Features (Python)
```python
from shared.licensing import license_client, requires_feature
from flask_security import auth_required

@app.route('/api/v1/advanced/analytics')
@auth_required()
@requires_feature("advanced_analytics")
def generate_advanced_report():
    """Requires authentication AND professional+ license"""
    return {'report': analytics.generate_report()}
```

### Monitoring Integration
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.route('/metrics')
def metrics():
    return generate_latest(), {'Content-Type': 'text/plain'}
```

## Troubleshooting & Support

### Common Issues
1. **Port Conflicts**: Check docker-compose port mappings
2. **Database Connections**: Verify connection strings and permissions
3. **License Validation Failures**: Check license key format and network connectivity
4. **Build Failures**: Check dependency versions and compatibility
5. **Test Failures**: Review test environment setup

### Debug Commands
```bash
# Container debugging
docker-compose logs -f service-name
docker exec -it container-name /bin/bash

# Application debugging
make debug                    # Start with debug flags
make logs                     # View application logs
make health                   # Check service health

# License debugging
make license-debug            # Test license server connectivity
make license-validate         # Validate current license
```

### Support Resources
- **Technical Documentation**: [Development Standards](docs/STANDARDS.md)
- **License Integration**: [License Server Guide](docs/licensing/license-server-integration.md)
- **Integration Support**: support@penguintech.io
- **Sales Inquiries**: sales@penguintech.io
- **License Server Status**: https://status.penguintech.io

## CI/CD & Workflows

### Documentation
- **Complete workflow documentation**: See [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md)
- **CI/CD standards and requirements**: See [`docs/STANDARDS.md`](docs/STANDARDS.md)

### Build Naming Conventions

All container images follow automatic naming based on branch and version changes:

| Scenario | Main Branch | Other Branches |
|----------|------------|-----------------|
| Regular build (no `.version` change) | `beta-<epoch64>` | `alpha-<epoch64>` |
| Version release (`.version` changed) | `vX.X.X-beta` | `vX.X.X-alpha` |
| Tagged release | `vX.X.X` + `latest` | N/A |

**Example**: Updating `.version` to `1.2.0` on main branch triggers builds tagged `v1.2.0-beta` (and auto-creates a GitHub pre-release).

### Version Management

- **Location**: `.version` file in repository root
- **Format**: Semantic versioning (e.g., `1.2.3`)
- **File tracking**: All workflows monitor `.version` for changes
- **Update command**: Edit `.version` file and commit
  ```bash
  echo "1.2.3" > .version
  git add .version
  git commit -m "Release v1.2.3"
  ```

### Pre-Commit Checklist

Before committing, run in this order:

- [ ] **Linters**: `npm run lint` or `golangci-lint run` or equivalent
- [ ] **Security scans**: `npm audit`, `gosec`, `bandit` (per language)
- [ ] **Tests**: `npm test`, `go test ./...`, `pytest` (unit tests only)
- [ ] **Version updates**: Update `.version` if releasing new version
- [ ] **Documentation**: Update docs if adding/changing workflows
- [ ] **No secrets**: Verify no credentials, API keys, or tokens in code
- [ ] **Docker builds**: Verify Dockerfile uses debian-slim base (no alpine)
- [ ] **API tests**: Run containerized API tests for modified services
- [ ] **Database**: Verify database configurations match DB_TYPE restrictions
- [ ] **Screenshots**: Update UI screenshots if UI changes made

**Only commit when asked** — follow the pre-commit checklist above, then wait for approval before `git commit`.

### Full Documentation

For complete workflow behavior, troubleshooting, and project-specific details, see [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md).

---

**Template Version**: 1.5.0
**Last Updated**: 2025-12-18
**Maintained by**: Penguin Tech Inc
**License Server**: https://license.penguintech.io

**Key Updates in v1.5.0:**
- **Shared Security Libraries**: Added `py_libs`, `go_libs`, `node_libs` with PyDAL-style validators
- **Mandatory Input Validation**: All API endpoints MUST use shared validators
- **Security Utilities**: Rate limiting, CSRF protection, secure headers, audit logging
- **Cryptographic Operations**: Argon2id/bcrypt hashing, AES-256-GCM encryption, secure tokens
- **gRPC Security Parity**: Same security interceptors for gRPC as REST APIs
- **Kubernetes Deployment**: Helm v3 charts, raw manifests, Kustomize overlays in `k8s/`
- **HTTP Utilities**: Request correlation, resilient HTTP client with retries
- **Linter Scripts**: Per-language linting scripts with venv/direnv support

**Key Updates in v1.4.0:**
- **Hybrid database approach**: SQLAlchemy for initialization, PyDAL for day-to-day operations
- Simplified DB_TYPE values: `postgres`, `mysql`, `sqlite` only
- Comprehensive MariaDB Galera cluster support with WSREP handling
- Galera retry decorator for WSREP_NOT_READY error handling

**Key Updates in v1.3.0:**
- Three-container architecture: Flask backend, Go backend, WebUI shell
- WebUI shell with Node.js + React, role-based access (Admin, Maintainer, Viewer)
- Flask backend with hybrid database support, JWT auth, user management
- Go backend with XDP/AF_XDP support, NUMA-aware memory pools
- GitHub Actions workflows for multi-arch builds (AMD64, ARM64)
- Gold text theme by default, Elder sidebar pattern, WaddlePerf tabs
- Docker Compose updated for new architecture

**Key Updates in v1.2.0:**
- Web UI and API as separate containers by default
- Mandatory linting for all languages (flake8, ansible-lint, eslint, etc.)
- CodeQL inspection compliance required
- Multi-database support by design (all PyDAL databases + MariaDB Galera)
- DB_TYPE environment variable with input validation
- Flask as sole web framework (PyDAL for database abstraction)

**Key Updates in v1.1.0:**
- Flask-Security-Too mandatory for authentication
- ReactJS as standard frontend framework
- Python 3.13 vs Go decision criteria
- XDP/AF_XDP guidance for high-performance networking
- WaddleAI integration patterns
- Release-mode license enforcement
- Performance optimization requirements (dataclasses with slots)

*This template provides a production-ready foundation for enterprise software development with comprehensive tooling, security, operational capabilities, and integrated licensing management.*
- ALL REST APIs MUST use versioning: `/api/v{major}/endpoint` format
- Semantic versioning for major versions only in URL
- Support current and previous versions (N-1) minimum
- Add deprecation headers to old versions
- Document migration paths for version changes

**Database Standards**:
- PyDAL mandatory for ALL Python applications
- Thread-safe usage with thread-local connections
- Environment variable configuration for all database settings
- Connection pooling and retry logic required

**Protocol Support**:
- REST API, gRPC, HTTP/1.1, HTTP/2, HTTP/3 support
- Environment variables for protocol configuration
- Multi-protocol implementation required

**Performance Optimization (Python):**
- Dataclasses with slots mandatory (30-50% memory reduction)
- Type hints required for all Python code
- asyncio for I/O-bound operations
- threading for blocking I/O
- multiprocessing for CPU-bound operations
- Avoid premature optimization - profile first

**High-Performance Networking (Case-by-Case):**
- XDP (eXpress Data Path): Kernel-level packet processing
- AF_XDP: Zero-copy socket for user-space packet processing
- Use only for network-intensive applications requiring >100K packets/sec
- Evaluate Python vs Go based on traffic requirements

**Microservices Architecture**:
- Web UI, API, and Connector as **separate containers by default**
- Single responsibility per service
- API-first design
- Independent deployment and scaling
- Each service has its own Dockerfile and dependencies

**Docker Standards**:
- Multi-arch builds (amd64/arm64)
- Debian-slim base images
- Docker Compose for local development
- Minimal host port exposure

**Testing**:
- Unit tests: Network isolated, mocked dependencies
- Integration tests: Component interactions
- E2E tests: Critical workflows
- Performance tests: Scalability validation

**Security**:
- TLS 1.2+ required
- Input validation mandatory
- JWT, MFA, mTLS standard
- SSO as enterprise feature

## Application Architecture

**ALWAYS use microservices architecture** - decompose into specialized, independently deployable containers:

1. **Web UI Container**: ReactJS frontend (separate container, served via nginx)
2. **Application API Container**: Flask + Flask-Security-Too backend (separate container)
3. **Connector Container**: External system integration (separate container)

**Default Container Separation**: Web UI and API are ALWAYS separate containers by default. This provides:
- Independent scaling of frontend and backend
- Different resource allocation per service
- Separate deployment lifecycles
- Technology-specific optimization

**Benefits**:
- Independent scaling
- Technology diversity
- Team autonomy
- Resilience
- Continuous deployment

📚 **Detailed Architecture Patterns**: See [Development Standards - Microservices Architecture](docs/STANDARDS.md#microservices-architecture)

## Common Integration Patterns

### Flask + Flask-Security-Too + PyDAL
```python
from flask import Flask
from flask_security import Security, SQLAlchemyUserDatastore, auth_required, hash_password
from pydal import DAL, Field
from dataclasses import dataclass
from typing import Optional

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')

# PyDAL database connection
db = DAL(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    pool_size=10
)

# Define tables with PyDAL
db.define_table('users',
    Field('email', 'string', requires=IS_EMAIL(), unique=True),
    Field('password', 'string'),
    Field('active', 'boolean', default=True),
    Field('fs_uniquifier', 'string', unique=True),
    migrate=True)

db.define_table('roles',
    Field('name', 'string', unique=True),
    Field('description', 'text'),
    migrate=True)

# Flask-Security-Too setup
from flask_security import Security, PyDALUserDatastore
user_datastore = PyDALUserDatastore(db, db.users, db.roles)
security = Security(app, user_datastore)

@app.route('/api/v1/protected')
@auth_required()
def protected_resource():
    return {'message': 'This is a protected endpoint'}

@app.route('/healthz')
def health():
    return {'status': 'healthy'}, 200
```

### Hybrid Database Strategy: SQLAlchemy + PyDAL

**Production Pattern**: Use **SQLAlchemy for schema initialization**, then **PyDAL for day-to-day operations**.

This approach combines SQLAlchemy's powerful migration and schema management with PyDAL's lightweight flexibility:
- **SQLAlchemy**: Alembic migrations, schema versioning, complex relationships
- **PyDAL**: Runtime query builder, simple CRUD, cross-database compatibility

**Database Support**: `DB_TYPE` restricted to **postgres, mysql, sqlite only**
- postgres: Default, supports all features
- mysql: Full support including MariaDB Galera clusters
- sqlite: Development and embedded deployments

**Environment Configuration**:
```bash
DB_TYPE=postgres              # Only: postgres, mysql, sqlite
DB_HOST=localhost
DB_PORT=5432
DB_USER=app_user
DB_NAME=app_db
DB_PASS=secure_password
DB_POOL_SIZE=10

# MariaDB Galera cluster (mysql only)
GALERA_MODE=false            # Set true for Galera-specific settings
GALERA_NODES=node1,node2,node3  # Comma-separated nodes
```

**Implementation**:
```python
from pydal import DAL, Field
from dataclasses import dataclass
import os

# RESTRICTED to: postgres, mysql, sqlite
VALID_DB_TYPES = {'postgres', 'mysql', 'sqlite'}

@dataclass(slots=True, frozen=True)
class UserModel:
    """User model with slots for memory efficiency"""
    id: int
    email: str
    name: str
    active: bool

def get_db_connection() -> DAL:
    """Initialize PyDAL with multi-database support (postgres/mysql/sqlite only)"""
    db_type = os.getenv('DB_TYPE', 'postgres').lower()

    # Strict validation - only postgres, mysql, sqlite
    if db_type not in VALID_DB_TYPES:
        raise ValueError(f"DB_TYPE must be postgres, mysql, or sqlite (got: {db_type})")

    # Build connection URI
    db_uri = f"{db_type}://" \
             f"{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@" \
             f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/" \
             f"{os.getenv('DB_NAME')}"

    # MariaDB Galera cluster configuration (mysql only)
    galera_mode = os.getenv('GALERA_MODE', 'false').lower() == 'true'

    dal_kwargs = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        'migrate_enabled': True,
        'check_reserved': ['all'],
        'lazy_tables': True
    }

    # Galera-specific: handle wsrep_sync_wait for read-your-writes consistency
    if galera_mode and db_type == 'mysql':
        dal_kwargs['driver_args'] = {
            'init_command': 'SET wsrep_sync_wait=1'
        }
        # Get Galera nodes if configured
        galera_nodes = os.getenv('GALERA_NODES', '').split(',')
        if galera_nodes and galera_nodes[0]:
            dal_kwargs['pool_pre_ping'] = True  # Enable pre-ping for failover

    return DAL(db_uri, **dal_kwargs)
```

**Schema Initialization** (SQLAlchemy via Alembic):
```bash
# One-time initialization
alembic upgrade head  # Apply all migrations

# Then use PyDAL for runtime operations
```

### ReactJS Frontend Integration
```javascript
// API client for Flask backend
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Protected component example
import React, { useEffect, useState } from 'react';

function ProtectedComponent() {
  const [data, setData] = useState(null);

  useEffect(() => {
    apiClient.get('/api/v1/protected')
      .then(response => setData(response.data))
      .catch(error => console.error('Error:', error));
  }, []);

  return <div>{data?.message}</div>;
}
```

### License-Gated Features (Python)
```python
from shared.licensing import license_client, requires_feature
from flask_security import auth_required

@app.route('/api/v1/advanced/analytics')
@auth_required()
@requires_feature("advanced_analytics")
def generate_advanced_report():
    """Requires authentication AND professional+ license"""
    return {'report': analytics.generate_report()}
```

### Monitoring Integration
```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.route('/metrics')
def metrics():
    return generate_latest(), {'Content-Type': 'text/plain'}
```

## Website Integration Requirements

**Each project MUST have two dedicated websites**:
- Marketing/Sales website (Node.js based)
- Documentation website (Markdown based)

**Website Design Preferences**:
- Multi-page design preferred
- Modern aesthetic with clean appearance
- Subtle, sophisticated color schemes
- Gradient usage encouraged
- Responsive design
- Performance focused

**Repository Integration**:
- Add `github.com/penguintechinc/website` as sparse checkout submodule
- Only include project-specific folders
- Folder naming: `{app_name}/` and `{app_name}-docs/`

## Troubleshooting & Support

### Common Issues
1. **Port Conflicts**: Check docker-compose port mappings
2. **Database Connections**: Verify connection strings and permissions
3. **License Validation Failures**: Check license key format and network connectivity
4. **Build Failures**: Check dependency versions and compatibility
5. **Test Failures**: Review test environment setup

### Debug Commands
```bash
# Container debugging
docker-compose logs -f service-name
docker exec -it container-name /bin/bash

# Application debugging
make debug                    # Start with debug flags
make logs                     # View application logs
make health                   # Check service health

# License debugging
make license-debug            # Test license server connectivity
make license-validate         # Validate current license
```

### Support Resources
- **Technical Documentation**: [Development Standards](docs/STANDARDS.md)
- **License Integration**: [License Server Guide](docs/licensing/license-server-integration.md)
- **Integration Support**: support@penguintech.io
- **Sales Inquiries**: sales@penguintech.io
- **License Server Status**: https://status.penguintech.io

## CI/CD & Workflows

### Documentation
- **Complete workflow documentation**: See [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md)
- **CI/CD standards and requirements**: See [`docs/STANDARDS.md`](docs/STANDARDS.md)

### Build Naming Conventions

All container images follow automatic naming based on branch and version changes:

| Scenario | Main Branch | Other Branches |
|----------|------------|-----------------|
| Regular build (no `.version` change) | `beta-<epoch64>` | `alpha-<epoch64>` |
| Version release (`.version` changed) | `vX.X.X-beta` | `vX.X.X-alpha` |
| Tagged release | `vX.X.X` + `latest` | N/A |

**Example**: Updating `.version` to `1.2.0` on main branch triggers builds tagged `v1.2.0-beta` (and auto-creates a GitHub pre-release).

### Version Management

- **Location**: `.version` file in repository root
- **Format**: Semantic versioning (e.g., `1.2.3`)
- **File tracking**: All workflows monitor `.version` for changes
- **Update command**: Edit `.version` file and commit
  ```bash
  echo "1.2.3" > .version
  git add .version
  git commit -m "Release v1.2.3"
  ```

### Pre-Commit Checklist

Before committing, run in this order:

- [ ] **Linters**: `npm run lint` or `golangci-lint run` or equivalent
- [ ] **Security scans**: `npm audit`, `gosec`, `bandit` (per language)
- [ ] **Tests**: `npm test`, `go test ./...`, `pytest` (unit tests only)
- [ ] **Version updates**: Update `.version` if releasing new version
- [ ] **Documentation**: Update docs if adding/changing workflows
- [ ] **No secrets**: Verify no credentials, API keys, or tokens in code
- [ ] **Docker builds**: Verify Dockerfile uses debian-slim base (no alpine)
- [ ] **API tests**: Run containerized API tests for modified services
- [ ] **Database**: Verify database configurations match DB_TYPE restrictions
- [ ] **Screenshots**: Update UI screenshots if UI changes made (`cd services/webui && npm run screenshots`)

**Only commit when asked** — follow the pre-commit checklist above, then wait for approval before `git commit`.

### Full Documentation

For complete workflow behavior, troubleshooting, and project-specific details, see [`docs/WORKFLOWS.md`](docs/WORKFLOWS.md).

## Template Customization

### Adding New Languages
1. Create language-specific directory structure
2. Add Dockerfile and build scripts
3. Update CI/CD pipeline configuration
4. Add language-specific linting and testing
5. Update documentation and examples

### Adding New Services
1. Use service template in `services/` directory
2. Configure service discovery and networking
3. Add monitoring and logging integration
4. Integrate license checking for service features
5. Create service-specific tests
6. Update deployment configurations

### Enterprise Integration
- Configure license server integration
- Set up multi-tenant data isolation
- Implement usage tracking and reporting
- Add compliance audit logging
- Configure enterprise monitoring

---

**Template Version**: 1.3.0
**Last Updated**: 2025-12-03
**Maintained by**: Penguin Tech Inc
**License Server**: https://license.penguintech.io

**Key Updates in v1.3.0:**
- Three-container architecture: Flask backend, Go backend, WebUI shell
- WebUI shell with Node.js + React, role-based access (Admin, Maintainer, Viewer)
- Flask backend with PyDAL, JWT auth, user management
- Go backend with XDP/AF_XDP support, NUMA-aware memory pools
- GitHub Actions workflows for multi-arch builds (AMD64, ARM64)
- Gold text theme by default, Elder sidebar pattern, WaddlePerf tabs
- Docker Compose updated for new architecture

**Key Updates in v1.2.0:**
- Web UI and API as separate containers by default
- Mandatory linting for all languages (flake8, ansible-lint, eslint, etc.)
- CodeQL inspection compliance required
- Multi-database support by design (all PyDAL databases + MariaDB Galera)
- DB_TYPE environment variable with input validation
- Flask as sole web framework (PyDAL for database abstraction)

**Key Updates in v1.1.0:**
- Flask-Security-Too mandatory for authentication
- ReactJS as standard frontend framework
- Python 3.13 vs Go decision criteria
- XDP/AF_XDP guidance for high-performance networking
- WaddleAI integration patterns
- Release-mode license enforcement
- Performance optimization requirements (dataclasses with slots)

*This template provides a production-ready foundation for enterprise software development with comprehensive tooling, security, operational capabilities, and integrated licensing management.*
