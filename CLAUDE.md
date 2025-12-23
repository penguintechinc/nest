# Project Template - Claude Code Context

## Project Overview

This is a comprehensive project template incorporating best practices and patterns from Penguin Tech Inc projects. It provides a standardized foundation for multi-language projects with enterprise-grade infrastructure and integrated licensing.

**Template Features:**
- Multi-language support (Go 1.23.x, Python 3.12/3.13, Node.js 18+)
- Enterprise security and licensing integration
- Comprehensive CI/CD pipeline
- Production-ready containerization
- Monitoring and observability
- Version management system
- PenguinTech License Server integration

## Technology Stack

### Languages & Frameworks
- **Go**: 1.23.x (latest patch version)
- **Python**: 3.12 for py4web applications (py4web has issues with 3.13), 3.13 for non-web applications
- **Node.js**: 18+ for sales/marketing websites and tooling only
- **JavaScript/TypeScript**: Modern ES2022+ standards

### Infrastructure & DevOps
- **Containers**: Docker with multi-stage builds, Docker Compose
- **Orchestration**: Kubernetes with Helm charts
- **Configuration Management**: Ansible for infrastructure automation
- **CI/CD**: GitHub Actions with comprehensive pipelines
- **Monitoring**: Prometheus metrics, Grafana dashboards
- **Logging**: Structured logging with configurable levels

### Databases & Storage
- **Primary**: PostgreSQL with connection pooling, non-root user/password, dedicated database
- **Cache**: Redis/Valkey with optional TLS and authentication
- **ORMs**: PyDAL for Python (supports MySQL, PostgreSQL, etc.), GORM for Go
- **Migrations**: Automated schema management
- **Database Support**: Use PyDAL only for databases with full PyDAL support

### Security & Authentication
- **TLS**: Enforce TLS 1.2 minimum, prefer TLS 1.3
- **HTTP3/QUIC**: Utilize UDP with TLS for high-performance connections where possible
- **Authentication**: JWT and MFA (standard), mTLS where applicable
- **SSO**: SAML/OAuth2 SSO as enterprise-only features
- **Secrets**: Environment variable management
- **Scanning**: Trivy vulnerability scanning, CodeQL analysis

## PenguinTech License Server Integration

All projects integrate with the centralized PenguinTech License Server at `https://license.penguintech.io` for feature gating and enterprise functionality.

**Key Points:**
- Universal JSON response format based on `.JSONDESIGN` specification
- Bearer token authentication using license keys (format: `PENG-XXXX-XXXX-XXXX-XXXX-ABCD`)
- Core endpoints: `/api/v2/validate`, `/api/v2/features`, `/api/v2/keepalive`

**For complete details see:** [docs/licensing/license-server-integration.md](docs/licensing/license-server-integration.md)
- Complete API specifications
- Python and Go client implementations
- Environment variable configuration
- Integration examples

## Project Structure

Standard project layout follows microservices architecture with multi-language support (Go, Python, Node.js).

**For complete directory tree and explanations see:** [docs/architecture/PROJECT_STRUCTURE.md](docs/architecture/PROJECT_STRUCTURE.md)

## Version Management System

### Format: vMajor.Minor.Patch.build
- **Major**: Breaking changes, API changes, removed features
- **Minor**: Significant new features and functionality additions
- **Patch**: Minor updates, bug fixes, security patches
- **Build**: Epoch64 timestamp of build time (used between releases for automatic chronological ordering)

### Version Update Process
```bash
# Update version using provided scripts
./scripts/version/update-version.sh          # Increment build timestamp
./scripts/version/update-version.sh patch    # Increment patch version
./scripts/version/update-version.sh minor    # Increment minor version
./scripts/version/update-version.sh major    # Increment major version
./scripts/version/update-version.sh 1 2 3    # Set specific version
```

### Version Integration
- Embedded in applications and API responses
- Docker images tagged with full version for dev, semantic for releases
- Automated version bumping in CI/CD pipeline
- Version validation in build processes

## Development Workflow

### Local Development Setup
```bash
# Clone and setup
git clone <repository-url>
cd project-name
make setup                    # Install dependencies and setup environment
make dev                      # Start development environment
```

### Essential Commands
```bash
# Development
make dev                      # Start development services
make test                     # Run all tests
make lint                     # Run linting and code quality checks
make build                    # Build all services
make clean                    # Clean build artifacts

# Production
make docker-build             # Build production containers
make docker-push              # Push to registry
make deploy-dev               # Deploy to development
make deploy-prod              # Deploy to production

# Testing
make test-unit               # Run unit tests
make test-integration        # Run integration tests
make test-e2e                # Run end-to-end tests
make test-performance        # Run performance tests

# License Management
make license-validate        # Validate license configuration
make license-check-features  # Check available features
```

## Security Requirements

### Input Validation
- ALL inputs MUST have appropriate validators
- Use framework-native validation (pydal validators, Go validation libraries)
- Implement XSS and SQL injection prevention
- Server-side validation for all client input
- CSRF protection using framework native features

### Authentication & Authorization
- Multi-factor authentication support
- Role-based access control (RBAC)
- API key management with rotation
- JWT token validation with proper expiration
- Session management with secure cookies

### Security Scanning
- Automated dependency vulnerability scanning
- Container image security scanning
- Static code analysis for security issues
- Regular security audit logging
- Secrets scanning in CI/CD pipeline

## Enterprise Features

### Licensing Integration
- PenguinTech License Server integration
- Feature gating based on license tiers
- Usage tracking and reporting
- Compliance audit logging
- Enterprise support escalation

### Multi-Tenant Architecture
- Customer isolation and data segregation
- Per-tenant configuration management
- Usage-based billing integration
- White-label capabilities
- Compliance reporting (SOC2, ISO27001)

### Monitoring & Observability
- Prometheus metrics collection
- Grafana dashboards for visualization
- Structured logging with correlation IDs
- Distributed tracing support
- Real-time alerting and notifications

## CI/CD Pipeline Features

### Testing Pipeline
- Multi-language testing (Go, Python, Node.js)
- Parallel test execution for performance
- Code coverage reporting
- Security scanning integration
- Performance regression testing

### Build Pipeline
- **Multi-architecture Docker builds** (amd64/arm64) using separate parallel workflows
- **Debian-slim base images** for all container builds to minimize size and attack surface
- **Parallel workflow execution** to minimize total build time without removing functionality
- **Optimized build times**: Prioritize speed while maintaining full functionality
- Dependency caching for faster builds
- Artifact management and versioning
- Container registry integration
- Build optimization and layer caching

### Deployment Pipeline
- Environment-specific deployment configs
- Blue-green deployment support
- Rollback capabilities
- Health check validation
- Automated database migrations

### Quality Gates
- Required code review process
- Automated testing requirements
- Security scan pass requirements
- Performance benchmark validation
- Documentation update verification

## Critical Development Rules

**Essential Rules:**
- **NEVER commit automatically** unless explicitly requested
- **NEVER push to remote repositories** under any circumstances
- **ALWAYS maintain .PLAN and .TODO files** for crash recovery (add to .gitignore)
- **ALWAYS check for security vulnerabilities** before commits (Dependabot, Socket.dev)
- **NEVER mark tasks as completed until successful build verification**
- **All builds MUST execute within Docker containers** (debian-slim base images)
- **Multi-architecture builds** (amd64/arm64) using parallel workflows

**For complete development rules see:** [docs/development/CRITICAL_RULES.md](docs/development/CRITICAL_RULES.md)
- Git workflow details
- Local state management procedures
- Dependency security requirements
- Docker and GitHub Actions standards
- Code quality requirements

## File Size Limits

- **Maximum file size**: 25,000 characters for ALL code and markdown files
- **Split large files**: Decompose into modules, libraries, or separate documents
- **CLAUDE.md exception**: Maximum 39,000 characters (only exception to 25K rule)
- **High-level approach**: CLAUDE.md contains high-level context and references detailed docs
- **Documentation strategy**: Create detailed documentation in `docs/` folder and link to them from CLAUDE.md
- **Keep focused**: Critical context, architectural decisions, and workflow instructions only
- **User approval required**: ALWAYS ask user permission before splitting CLAUDE.md files
- **Use Task Agents**: Utilize task agents (subagents) to be more expedient and efficient when making changes to large files, updating or reviewing multiple files, or performing complex multi-step operations
- **Avoid sed/cat**: Use sed and cat commands only when necessary; prefer dedicated Read/Edit/Write tools for file operations

## Task Agent Usage Guidelines

**Model Selection:**
- **Haiku model**: Use for the majority of task agent work (file searches, simple edits, routine operations)
- **Sonnet model**: Use for more complex jobs requiring deeper reasoning (architectural decisions, complex refactoring, multi-file coordination)
- Default to haiku unless the task explicitly requires complex analysis

**Response Size Requirements:**
- **CRITICAL**: Task agents MUST return minimal responses to avoid context overload of the orchestration model
- Agents should return only essential information: file paths, line numbers, brief summaries
- Avoid returning full file contents or verbose explanations in agent responses
- Use bullet points and concise formatting in agent outputs

**Concurrency Limits:**
- **Maximum 10 task agents** running concurrently at any time
- Even with minimal responses, running more than 10 agents risks context overload
- Queue additional tasks if the limit would be exceeded
- Monitor active agent count before spawning new agents

**Best Practices:**
- Provide clear, specific prompts to agents to get focused responses
- Request only the information needed, not comprehensive analysis
- Use agents for parallelizable work (searching multiple directories, checking multiple files)
- Combine related small tasks into single agent calls when possible

## Pre-Commit Screenshots

**Run screenshot tool to update UI screenshots in documentation**:
- Run `cd services/webui && npm run screenshots` to capture current UI state
- This automatically removes old screenshots and captures fresh ones
- Commit updated screenshots with relevant feature/documentation changes
- Screenshots should be included in PRs for UI changes to document visual impact

## API Versioning Standards

- **ALL REST APIs MUST use versioning**: `/api/v{major}/endpoint` format
- **Semantic versioning**: Use semantic versioning for major versions only in URL
- **Version support**: Support current and previous versions (N-1) minimum
- **Deprecation headers**: Add deprecation headers to old versions
- **Migration documentation**: Document migration paths for version changes
- **Backward compatibility**: Maintain backward compatibility within major versions where possible

### Unit Testing Requirements
- **All applications MUST have comprehensive unit tests**
- **Network isolation**: Unit tests must NOT require external network connections
- **No external dependencies**: Cannot reach databases, APIs, or external services
- **Use mocks/stubs**: Mock all external dependencies and I/O operations
- **KISS principle**: Keep unit tests simple, focused, and fast
- **Test isolation**: Each test should be independent and repeatable
- **Fast execution**: Unit tests should complete in milliseconds, not seconds

### Performance Best Practices

**Always implement async/concurrent patterns** to maximize CPU and memory utilization:
- **Python:** asyncio, threading, multiprocessing with modern optimizations (dataclasses with slots, type hints)
- **Go:** Goroutines, channels, and runtime scheduler
- **Networking:** eBPF/XDP, AF_XDP, NUMA-aware memory allocation, zero-copy techniques
- **Database:** Connection pooling, prepared statements, query optimization

**For complete performance guidelines see:** [docs/development/PERFORMANCE.md](docs/development/PERFORMANCE.md)

### Documentation
- **README.md**: Keep as overview and pointer to comprehensive docs/ folder
- **docs/ folder**: Create comprehensive documentation for all aspects
- **RELEASE_NOTES.md**: Maintain in docs/ folder, prepend new version releases to top
- Update CLAUDE.md when adding significant context
- API documentation must be comprehensive
- Architecture decisions should be documented
- Security procedures must be documented

### README.md Standards
- **ALWAYS include build status badges** at the top of every README.md:
  - CI/CD pipeline status (GitHub Actions)
  - Test coverage status (Codecov)
  - Go Report Card (for Go projects)
  - Version badge
  - License badge (Limited AGPL3 with preamble for fair use)
- **ALWAYS include catchy ASCII art** below the build status badges
  - Use project-appropriate ASCII art that reflects the project's identity
  - Keep ASCII art clean and professional
  - Place in code blocks for proper formatting
- **Company homepage reference**: All project READMEs and sales websites should point to **www.penguintech.io** as the company's homepage
- **License standard**: All projects use Limited AGPL3 with preamble for fair use, not MIT

### CLAUDE.md File Management
- **Primary file**: Maintain main CLAUDE.md at project root
- **Split files when necessary**: For large/complex projects, create app-specific CLAUDE.md files
- **File structure for splits**:
  - `projectroot/CLAUDE.md` - Main context and cross-cutting concerns
  - `projectroot/app-folder/CLAUDE.md` - App-specific context and instructions
- **Root file linking**: Main CLAUDE.md should reference and link to app-specific files
- **User approval required**: ALWAYS ask user permission before splitting CLAUDE.md files
- **Split criteria**: Only split for genuinely large situations where single file becomes unwieldy

### Application Architecture Requirements

**Key Requirements:**
- **py4web primary** for all application web structures (sales/docs websites exempt)
- **Health endpoints:** ALL applications must implement `/healthz` endpoint
- **Metrics endpoints:** Prometheus metrics endpoint required
- **Logging:** Multi-destination support (console, UDP syslog, HTTP3/QUIC to Kafka)
- **Security:** TLS 1.2+ minimum, HTTP3/QUIC where possible, JWT/MFA/mTLS standard
- **Database:** PostgreSQL default with PyDAL, Redis/Valkey caching

**For complete architecture requirements see:** [docs/architecture/APPLICATION_ARCHITECTURE.md](docs/architecture/APPLICATION_ARCHITECTURE.md)
- Web framework standards
- Logging levels and destinations
- Security implementation details
- Ansible integration requirements
- Website integration with sparse submodules

## Common Integration Patterns

Standard integration patterns with working code examples are available for:
- License-gated features (Python/Go decorators and middleware)
- Database integration (PyDAL/GORM examples)
- API development (py4web/Gin frameworks)
- Monitoring integration (Prometheus metrics)

**For complete code examples see:** [docs/development/INTEGRATION_PATTERNS.md](docs/development/INTEGRATION_PATTERNS.md)

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

### License Server Support
- **Technical Documentation**: Complete API reference available
- **Integration Support**: support@penguintech.io
- **Sales Inquiries**: sales@penguintech.io
- **License Server Status**: https://status.penguintech.io

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

**Template Version**: 1.0.0
**Last Updated**: 2025-09-23
**Maintained by**: Penguin Tech Inc
**License Server**: https://license.penguintech.io

*This template provides a production-ready foundation for enterprise software development with comprehensive tooling, security, operational capabilities, and integrated licensing management.*