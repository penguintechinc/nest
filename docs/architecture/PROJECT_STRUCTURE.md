# Project Structure

## Overview

This document describes the standard project layout for Penguin Tech Inc applications. The structure provides a comprehensive foundation for multi-language projects with enterprise-grade infrastructure, security, and integrated licensing. This standardized layout ensures consistency across all projects and facilitates team collaboration, onboarding, and maintenance.

The directory structure is designed to support:
- **Multi-language development** (Go, Python, Node.js)
- **Microservices architecture** with clear separation of concerns
- **Scalable infrastructure** with containerization and orchestration
- **Enterprise security** and compliance requirements
- **Comprehensive testing** at multiple levels
- **Production-ready deployment** with CI/CD automation
- **PenguinTech License Server integration** for feature gating

Each major directory serves a specific purpose within the project ecosystem, allowing teams to locate and manage code, infrastructure, documentation, and configuration efficiently.

## Directory Tree

```
project-name/
├── .github/
│   ├── workflows/           # CI/CD pipelines
│   ├── ISSUE_TEMPLATE/      # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
├── apps/                    # Application code
│   ├── api/                 # API services (Go/Python)
│   ├── web/                 # Web applications (Python/Node.js)
│   └── cli/                 # CLI tools (Go)
├── services/                # Microservices
│   ├── service-name/
│   │   ├── cmd/             # Go main packages
│   │   ├── internal/        # Private application code
│   │   ├── pkg/             # Public library code
│   │   ├── Dockerfile       # Service container
│   │   └── go.mod           # Go dependencies
├── shared/                  # Shared components
│   ├── auth/                # Authentication utilities
│   ├── config/              # Configuration management
│   ├── database/            # Database utilities
│   ├── licensing/           # License server integration
│   ├── monitoring/          # Metrics and logging
│   └── types/               # Shared types/schemas
├── web/                     # Frontend applications
│   ├── public/              # Static assets
│   ├── src/                 # Source code
│   ├── package.json         # Node.js dependencies
│   └── Dockerfile           # Web container
├── infrastructure/          # Infrastructure as code
│   ├── docker/              # Docker configurations
│   ├── k8s/                 # Kubernetes manifests
│   ├── helm/                # Helm charts
│   └── monitoring/          # Prometheus/Grafana configs
├── scripts/                 # Utility scripts
│   ├── build/               # Build automation
│   ├── deploy/              # Deployment scripts
│   ├── test/                # Testing utilities
│   └── version/             # Version management
├── tests/                   # Test suites
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── e2e/                 # End-to-end tests
│   └── performance/         # Performance tests
├── docs/                    # Documentation
│   ├── api/                 # API documentation
│   ├── deployment/          # Deployment guides
│   ├── development/         # Development setup
│   ├── licensing/           # License integration guide
│   ├── architecture/        # System architecture
│   └── RELEASE_NOTES.md     # Version release notes (prepend new releases)
├── config/                  # Configuration files
│   ├── development/         # Dev environment configs
│   ├── production/          # Production configs
│   └── testing/             # Test environment configs
├── docker-compose.yml       # Development environment
├── docker-compose.prod.yml  # Production environment
├── Makefile                 # Build automation
├── go.mod                   # Go workspace
├── requirements.txt         # Python dependencies
├── package.json             # Node.js workspace
├── .version                 # Version tracking
├── VERSION.md               # Versioning guidelines
├── README.md                # Project documentation
├── CONTRIBUTING.md          # Contribution guidelines
├── SECURITY.md              # Security policies
├── LICENSE.md               # License information
└── CLAUDE.md                # Project context and guidelines
```

## Directory Descriptions

### `.github/`
Contains GitHub-specific configuration and automation:
- **`workflows/`** - GitHub Actions CI/CD pipeline definitions
- **`ISSUE_TEMPLATE/`** - Issue templates for bug reports and features
- **`PULL_REQUEST_TEMPLATE.md`** - Standard pull request template

### `apps/`
Primary application code organized by type:
- **`api/`** - REST or gRPC API services (built with Go or Python)
- **`web/`** - Web applications (py4web for Python, Next.js for Node.js)
- **`cli/`** - Command-line tools (Go preferred for CLI applications)

### `services/`
Microservices with standardized Go project layout:
- **`service-name/`** - Individual microservice
  - **`cmd/`** - Main entry points for executable services
  - **`internal/`** - Private application code not exported
  - **`pkg/`** - Public library code that can be imported by other packages
  - **`Dockerfile`** - Container definition for the service
  - **`go.mod`** - Go module definition and dependencies

### `shared/`
Shared libraries and utilities used across multiple services:
- **`auth/`** - Authentication and authorization utilities
- **`config/`** - Configuration management and parsing
- **`database/`** - Database connection pooling and utilities
- **`licensing/`** - PenguinTech License Server integration
- **`monitoring/`** - Prometheus metrics and logging infrastructure
- **`types/`** - Shared data structures and schemas

### `web/`
Frontend application code (typically Node.js/React/Vue):
- **`public/`** - Static assets (images, icons, fonts)
- **`src/`** - React/Vue component source code
- **`package.json`** - Node.js dependencies and scripts
- **`Dockerfile`** - Container definition for frontend

### `infrastructure/`
Infrastructure as Code and DevOps configurations:
- **`docker/`** - Docker build contexts and base configurations
- **`k8s/`** - Kubernetes manifests for production deployment
- **`helm/`** - Helm charts for Kubernetes deployment
- **`monitoring/`** - Prometheus scrape configs and Grafana dashboard definitions

### `scripts/`
Utility scripts for development and deployment:
- **`build/`** - Build automation and compilation scripts
- **`deploy/`** - Deployment and release scripts
- **`test/`** - Test utilities and helpers
- **`version/`** - Version management and update scripts

### `tests/`
Test suites organized by testing level:
- **`unit/`** - Fast, isolated unit tests with no external dependencies
- **`integration/`** - Tests that verify component interactions
- **`e2e/`** - End-to-end tests validating complete workflows
- **`performance/`** - Performance and load testing

### `docs/`
Comprehensive documentation:
- **`api/`** - API endpoint documentation and examples
- **`deployment/`** - Deployment procedures and runbooks
- **`development/`** - Development setup and guidelines
- **`licensing/`** - License server integration documentation
- **`architecture/`** - System architecture and design decisions
- **`RELEASE_NOTES.md`** - Version release notes (new releases prepended to top)

### `config/`
Environment-specific configuration files:
- **`development/`** - Local development settings
- **`production/`** - Production environment settings
- **`testing/`** - Test environment settings

### Root-level Files
- **`docker-compose.yml`** - Development environment with all services
- **`docker-compose.prod.yml`** - Production-like environment setup
- **`Makefile`** - Build automation targets and development commands
- **`go.mod`** - Go workspace module definition
- **`requirements.txt`** - Python dependencies
- **`package.json`** - Node.js workspace configuration
- **`.version`** - Current application version
- **`VERSION.md`** - Versioning guidelines and format
- **`README.md`** - Project overview and quick start
- **`CONTRIBUTING.md`** - Contribution guidelines
- **`SECURITY.md`** - Security policies and disclosure procedures
- **`LICENSE.md`** - License information and terms
- **`CLAUDE.md`** - Project context, guidelines, and development standards

## Best Practices

### Code Organization
- Keep related code together; avoid spreading functionality across multiple files
- Use packages/modules to logically group related functionality
- Public interfaces in `pkg/`, private implementation in `internal/`
- Share common utilities through the `shared/` directory

### Testing Strategy
- Write unit tests for all business logic
- Ensure unit tests have no external dependencies
- Use integration tests to verify component interactions
- Implement e2e tests for critical user workflows
- Maintain 80%+ code coverage target

### Documentation
- Keep README.md as an overview with links to detailed docs
- Document architecture decisions in `docs/architecture/`
- Maintain API documentation in `docs/api/`
- Update RELEASE_NOTES.md when releasing new versions

### Configuration Management
- Environment-specific configs in `config/` directory
- Use environment variables for sensitive data
- Never commit secrets or credentials
- Document all configuration options

### Containerization
- Use Debian-slim base images for optimal size and security
- Implement multi-stage builds for production images
- Tag images with semantic versions
- Store Dockerfiles in service root directories

### Deployment
- Use Kubernetes manifests for production deployments
- Implement Helm charts for package management
- Maintain separate dev and production compose files
- Include health checks and readiness probes

## Related Documentation

For more information about specific aspects of the project structure:
- See `docs/architecture/` for detailed architecture decisions
- See `docs/deployment/` for deployment procedures
- See `docs/development/` for development setup
- See `docs/licensing/` for license server integration
- See `CLAUDE.md` for comprehensive project guidelines

---

**Last Updated**: 2025-12-23
**Version**: 1.0.0
