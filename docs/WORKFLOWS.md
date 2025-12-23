# Workflow Documentation Template

This template provides a comprehensive structure for documenting CI/CD workflows. Copy this to `docs/WORKFLOWS.md` and customize the project-specific sections.

---

## Table of Contents

1. [Overview](#overview)
2. [Documentation Index](#documentation-index)
3. [Workflow Architecture](#workflow-architecture)
4. [Build Packages & Services](#build-packages--services)
5. [Naming Conventions](#naming-conventions)
6. [Path Filter Requirements](#path-filter-requirements)
7. [Security Scanning](#security-scanning)
8. [Version Release Workflow](#version-release-workflow)
9. [Build Optimization](#build-optimization)
10. [Local Testing](#local-testing)
11. [Troubleshooting](#troubleshooting)
12. [Project-Specific Configuration](#project-specific-configuration)

---

## Overview

This project uses GitHub Actions for continuous integration and deployment (CI/CD). Workflows are organized by build package (service/application), with each workflow handling:

- **Code Linting & Quality Checks**: Language-specific static analysis
- **Security Scanning**: Dependencies, code vulnerabilities, container images
- **Unit Testing**: Component-level testing with mocked external dependencies
- **Build & Push**: Multi-architecture Docker image builds (AMD64, ARM64)
- **Automated Versioning**: Semantic versioning with epoch64 timestamps
- **Pre-Release Creation**: Automatic GitHub pre-release generation on version changes

**Key Philosophy**: All workflows are optimized for **speed, reliability, and security**. Path filters ensure workflows only run when relevant files change, saving CI/CD resources.

---

## Documentation Index

This WORKFLOWS.md document is part of a comprehensive workflow documentation set:

- **[WORKFLOWS.md](WORKFLOWS.md)** (this file) - Main workflow guide with architecture, naming conventions, and quick reference
- **[WORKFLOWS-TROUBLESHOOTING.md](WORKFLOWS-TROUBLESHOOTING.md)** - Complete troubleshooting guide with common errors, debugging procedures, and solutions
- **[WORKFLOWS-SECURITY.md](WORKFLOWS-SECURITY.md)** - Security scanning configuration, vulnerability management, and compliance procedures

---

## Workflow Architecture

### Pipeline Structure

Each build package has a dedicated workflow file following this structure:

```
┌──────────────┐
│ Lint Stage   │ (Fail fast on code quality issues)
└───────┬──────┘
        │
        ▼
┌──────────────┐
│ Test Stage   │ (Unit tests only, mocked dependencies)
└───────┬──────┘
        │
        ▼
┌──────────────────────┐
│ Build & Push Stage   │ (Docker image build for multi-arch)
└───────┬──────────────┘
        │
        ▼
┌──────────────────────┐
│ Security Scan Stage  │ (Trivy container scan, CodeQL)
└──────────────────────┘
```

### Job Dependencies

- **Lint** → Runs immediately on push/PR
- **Test** → Requires lint to pass (fails fast on quality)
- **Build** → Requires both lint and test to pass
- **Security Scan** → Runs after build on push to registr

### When Workflows Trigger

Workflows trigger when:
1. Code changes in the build package directory
2. `.version` file changes (ensures version updates trigger all builds)
3. The workflow file itself changes
4. Manual trigger via `workflow_dispatch`

**Branches**: Main workflow triggers on `main` and `develop` branches. Pull requests trigger on `main` branch only.

---

## Build Packages & Services

### What is a Build Package?

A build package is a single, independently deployable service or application. For containerized services, the build package includes builds for multiple architectures:

- `linux/amd64` - Intel/AMD 64-bit servers
- `linux/arm64` - ARM 64-bit (Apple Silicon, Graviton, etc.)

### Project Services

**Project Template** includes three services:

| Service | Directory | Dockerfile | Architectures | Notes |
|---------|-----------|-----------|---------------|-------|
| flask-backend | `services/flask-backend/` | `services/flask-backend/Dockerfile` | amd64, arm64 | Python 3.13, Flask, PyDAL |
| go-backend | `services/go-backend/` | `services/go-backend/Dockerfile` | amd64, arm64 | Go 1.23, high-performance networking |
| webui | `services/webui/` | `services/webui/Dockerfile` | amd64, arm64 | Node.js 18+, React frontend |

### Workflow Files

Each service has a corresponding workflow file:

```
.github/workflows/
├── build-flask-backend.yml    # Flask backend build pipeline
├── build-go-backend.yml       # Go backend build pipeline
├── build-webui.yml            # WebUI build pipeline
└── version-release.yml        # Version-based pre-release creation
```

---

## Naming Conventions

### Overview

Image naming follows strict patterns based on:
1. **Build trigger type**: Code change or version change
2. **Branch**: Main branch vs development branches
3. **Release**: Official release tags

### Pattern Reference

#### Regular Builds (No Version Change)

When code changes but `.version` file doesn't change:

**Main Branch**:
```
image-name:beta-<epoch64>
```
Example: `my-service:beta-1702000000`

**Development Branches** (develop, feature/*, etc):
```
image-name:alpha-<epoch64>
```
Example: `my-service:alpha-1702000000`

#### Version Builds (Version Change)

When `.version` file changes (indicates intentional version bump):

**Main Branch**:
```
image-name:vX.X.X-beta
```
Example: `my-service:v1.2.3-beta`

**Development Branches**:
```
image-name:vX.X.X-alpha
```
Example: `my-service:v1.2.3-alpha`

#### Release Tags (Official Releases)

When pushing a release tag (`v*`):
```
image-name:vX.X.X      # Primary release version
image-name:latest      # Latest release pointer
```
Example: `my-service:v1.2.3` and `my-service:latest`

### Naming Explanation

| Pattern | When Used | Example | Purpose |
|---------|-----------|---------|---------|
| `beta-<epoch64>` | Code change on main | `beta-1702000000` | Track beta builds, know exact build time |
| `alpha-<epoch64>` | Code change on develop | `alpha-1702000000` | Track development snapshots |
| `vX.X.X-beta` | Version change on main | `v1.2.3-beta` | Pre-release version tracking |
| `vX.X.X-alpha` | Version change on develop | `v1.2.3-alpha` | Development version tracking |
| `vX.X.X` | Official release | `v1.2.3` | Stable release version |
| `latest` | Latest stable | `latest` | Always points to newest release |

### Epoch64 Timestamp

The `<epoch64>` value is the Unix timestamp (seconds since January 1, 1970 UTC) at build time.

- **Generation**: `date +%s` produces the epoch timestamp
- **Uniqueness**: Each build has a unique timestamp
- **Sortability**: Timestamps sort chronologically
- **Example**: `1702000000` = November 8, 2023, 7:26:40 PM UTC

**Benefits**:
- Know exactly when an image was built
- Identify which exact code is running in production
- Trace issues to specific points in time
- Unique identification without human naming

### Version File Format

The `.version` file contains semantic versioning:

```
X.Y.Z
```

Where:
- **X**: Major version (breaking changes, API changes)
- **Y**: Minor version (new features, backward compatible)
- **Z**: Patch version (bug fixes, patches)

Example: `1.2.3`

**Update Commands**:
```bash
# Increment patch (bug fix)
echo "1.2.4" > .version

# Increment minor (new feature)
echo "1.3.0" > .version

# Increment major (breaking change)
echo "2.0.0" > .version
```

---

## Path Filter Requirements

### Why Path Filters Matter

Path filters optimize CI/CD by:
- **Reducing build time**: Don't rebuild unrelated services
- **Saving costs**: Fewer GitHub Actions minutes used
- **Faster feedback**: Developers get results quicker
- **Isolation**: Changes in one service don't trigger others

### Standard Path Filter Pattern

Every build workflow must include these paths:

```yaml
on:
  push:
    branches: [main, develop]
    paths:
      - 'services/[service-name]/**'    # Service code
      - '.version'                       # Critical: trigger on version changes
      - '.github/workflows/build-[service-name].yml'  # Workflow itself
  pull_request:
    branches: [main]
    paths:
      - 'services/[service-name]/**'
      - '.version'
      - '.github/workflows/build-[service-name].yml'
```

### Critical: .version in All Path Filters

**IMPORTANT**: The `.version` file MUST be in path filters for all build workflows. This ensures:

1. **Triggered Rebuilds**: When version changes, all services rebuild
2. **Consistent Versioning**: All images from same commit have same version
3. **Release Automation**: Pre-releases only trigger for intentional version bumps
4. **Audit Trail**: Clear separation between code changes and version bumps

### Path Filter Examples

**Good ✅**:
```yaml
paths:
  - 'services/flask-backend/**'
  - '.version'
  - '.github/workflows/build-flask-backend.yml'
```

**Bad ❌** (Missing .version):
```yaml
paths:
  - 'services/flask-backend/**'
  - '.github/workflows/build-flask-backend.yml'
```

**Bad ❌** (Paths too broad):
```yaml
paths:
  - 'services/**'  # Triggers for ALL services
  - '**'           # Triggers for everything
```

### Shared Code Path Filters

If services share code (e.g., in `shared/` directory), include it:

```yaml
paths:
  - 'services/[service-name]/**'
  - 'shared/**'                      # Add if shared code is used
  - '.version'
  - '.github/workflows/build-[service-name].yml'
```

---

## Security Scanning

For detailed security scanning configuration, vulnerability management, and compliance procedures, see:

**[WORKFLOWS-SECURITY.md](WORKFLOWS-SECURITY.md)** - Complete security scanning guide with:
- Trivy vulnerability scanning configuration
- CodeQL security analysis setup
- Language-specific security checks (Python/Go/Node.js)
- Dependency vulnerability checks and remediation
- Security compliance requirements
- Alert response workflows

**Quick Overview**: Each workflow includes dependency scanning, code analysis, container scanning (Trivy), and secret scanning. Security checks run early in the pipeline for fast feedback.

---

## Version Release Workflow

### Overview

The `version-release.yml` workflow automatically creates GitHub pre-releases when `.version` file changes on the main branch.

### Workflow Behavior

**Trigger**: `.version` file change on `main` branch

**Actions**:
1. Read `.version` file and extract semantic version
2. Check if version is not default (0.0.0)
3. Check if release already exists
4. Generate release notes from commit history
5. Create GitHub pre-release with auto-generated notes
6. Skip if version is 0.0.0 or release already exists

### Release Lifecycle

```
Developer updates .version file
         │
         ▼
        Commit on main branch
         │
         ▼
       Push to GitHub
         │
         ▼
version-release.yml triggers
         │
         ├─→ Extract version from .version file
         │
         ├─→ Check if 0.0.0 (skip if true)
         │
         ├─→ Check if release exists (skip if true)
         │
         └─→ Create pre-release with notes
         │
         ▼
GitHub pre-release created & visible
```

### Manual Release Creation

If pre-release workflow doesn't create release:

```bash
# From project root with .version file
VERSION=$(cat .version)
gh release create "v$VERSION" \
  --title "v$VERSION" \
  --notes "Release notes here" \
  --prerelease
```

### Converting Pre-Release to Release

To convert pre-release to full release:

```bash
# Mark as final release (remove pre-release flag)
gh release edit "vX.X.X" --prerelease=false
```

### Build Workflow Interaction

Build workflows (build-[service].yml) interact with version-release.yml:

1. **Regular code change** → Build workflow triggers → `beta-<epoch64>` or `alpha-<epoch64>` tags
2. **Version change** → Build workflow triggers AND version-release workflow triggers
   - Build workflow: Creates `vX.X.X-beta` or `vX.X.X-alpha` images
   - Version-release: Creates GitHub pre-release

---

## Build Optimization

### Multi-Architecture Builds

All Docker builds target multiple architectures:

```yaml
platforms: linux/amd64,linux/arm64
```

This creates images for:
- **linux/amd64**: Intel/AMD 64-bit servers
- **linux/arm64**: Apple Silicon, AWS Graviton, ARM servers

Benefits:
- Single image works across architectures
- Automatic architecture selection when pulling
- Future-proof for ARM adoption

### GitHub Actions Cache

Builds use GitHub Actions cache for faster builds:

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**How it works**:
- First build: Takes full time, stores cache
- Subsequent builds: Reuse cached layers (often 50-80% faster)
- Cache includes: Base image, dependencies, intermediate steps

### Docker Build Caching Strategy

**Layer caching order** (from slowest to fastest to change):

1. **Base image** (rarely changes) → Cached longest
2. **System dependencies** (change occasionally) → Medium cache
3. **Application dependencies** (change per commit) → Regular cache
4. **Application code** (always changes) → Not cached

Dockerfile best practices for caching:

```dockerfile
# Good - dependencies before code
FROM debian:12-slim
RUN apt-get update && apt-get install -y python3 pip
COPY requirements.txt .
RUN pip install -r requirements.txt    # Cached unless requirements change
COPY . /app                             # Only invalidates if app code changes

# Bad - invalidates cache on every code change
FROM debian:12-slim
COPY . /app
RUN apt-get update && apt-get install -y python3 pip
RUN pip install -r requirements.txt
```

### Path-Based Execution

Workflows only run when relevant paths change:

```yaml
paths:
  - 'services/flask-backend/**'  # Only run if Flask backend changes
  - '.version'                    # Only run if version changes
  - '.github/workflows/build-flask-backend.yml'
```

**Example savings**:
- 10 services, 1 changes → Run 1 workflow instead of 10
- Each workflow: 5-15 minutes → Save 45-135 minutes CI time
- 20 commits/day × 18 projects → Save hours of CI time daily

### Build Optimization Checklist

- ✅ Multi-architecture builds enabled (amd64, arm64)
- ✅ GitHub Actions cache enabled
- ✅ Path filters configured correctly
- ✅ Dockerfile layers optimized for caching
- ✅ Minimal base images (Debian slim, not Alpine)
- ✅ Multi-stage builds if applicable
- ✅ Unused dependencies removed

---

## Local Testing

### Prerequisites

Ensure you have:

```bash
# Docker for building/running containers
docker --version          # Docker 24+
docker-compose --version  # Docker Compose 2+

# Language runtimes
python --version          # 3.13+ for Python services
go version                # 1.23+ for Go services
node --version            # 18+ for Node.js services
```

### Testing Before Commit

**Always run these checks locally before committing**:

```bash
# 1. Linting (catches code quality issues first)
cd services/[service-name]
npm run lint           # For Node.js services
# OR
python -m flake8 .     # For Python services
# OR
golangci-lint run      # For Go services

# 2. Security checks (catches vulnerable dependencies)
npm audit --audit-level=high      # Node.js
python -m safety check            # Python
go mod audit                       # Go
bandit -r .                        # Python

# 3. Unit tests (verify functionality)
npm test               # Node.js
pytest                 # Python
go test ./...          # Go

# 4. Build locally
docker-compose build [service-name]

# 5. Run locally
docker-compose up [service-name]
```

### Local Docker Compose Testing

Test entire stack locally:

```bash
# Start all services
docker-compose up

# In another terminal, test endpoints
curl http://localhost:5000/api/health      # Flask backend
curl http://localhost:3000/                # React UI
curl http://localhost:8080/health          # Go backend (if present)

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down
```

### Common Testing Patterns

#### Python Service Testing

```bash
cd services/flask-backend

# Install dependencies
pip install -r requirements.txt

# Run linting
flake8 app
black --check app
isort --check-only app

# Run security check
bandit -r app -ll

# Run tests
pytest --cov=app

# Build Docker image
docker build -t my-service:test .
```

#### Go Service Testing

```bash
cd services/go-backend

# Download dependencies
go mod download

# Run linting
golangci-lint run

# Run tests
go test -v -race ./...

# Build binary
go build -o my-service main.go

# Build Docker image
docker build -t my-service:test .
```

#### Node.js Service Testing

```bash
cd services/webui

# Install dependencies
npm install

# Run linting
npm run lint

# Run security audit
npm audit --audit-level=high

# Run tests
npm test

# Build
npm run build

# Build Docker image
docker build -t my-service:test .
```

### Troubleshooting Local Tests

**Issue**: `Port already in use`
```bash
# Find process using port
lsof -i :5000

# Kill process or change docker-compose port
docker-compose down  # Stop running containers
```

**Issue**: `Module not found` / `Package not found`
```bash
# Reinstall dependencies
rm -rf node_modules && npm install    # Node.js
rm -rf venv && python -m venv venv    # Python
go clean -modcache && go mod download # Go
```

**Issue**: `Docker image build fails`
```bash
# Check Dockerfile syntax
docker build -t test:latest --no-cache services/[service]

# View detailed build output
docker build --progress=plain -t test:latest services/[service]
```

---

## Troubleshooting

For comprehensive troubleshooting guides, common errors, and debugging procedures, see:

**[WORKFLOWS-TROUBLESHOOTING.md](WORKFLOWS-TROUBLESHOOTING.md)** - Complete troubleshooting guide with:
- Workflow execution issues (triggers, builds, authentication)
- Container build problems and solutions
- Version and naming issues
- Permission and authentication errors
- Slow build optimization
- Debugging checklists and procedures

**Quick Overview**: Most issues fall into: workflow trigger problems (check path filters), build failures (check logs), security scan failures (update dependencies), or slow builds (check caching).

---

## Project-Specific Configuration

### Service Registry

**Project Template Services**:

| Service | Language | Path | Tests | Security | Notes |
|---------|----------|------|-------|----------|-------|
| flask-backend | Python | `services/flask-backend/` | pytest | bandit, safety check | Python 3.13, Flask, PyDAL |
| go-backend | Go | `services/go-backend/` | go test | gosec, go mod audit | Go 1.23, high-performance networking |
| webui | Node.js | `services/webui/` | jest | npm audit | React frontend, Node.js 18+ |

### Custom Variables

**DEFINE THESE** at the top of build workflows:

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/[service-name]
  [SERVICE_SPECIFIC_VAR]: value
```

### Environment Variables

**Required at build time**:

| Variable | Source | Usage | Example |
|----------|--------|-------|---------|
| `GITHUB_TOKEN` | GitHub | Registry auth, release creation | Auto-provided |
| `DB_TYPE` | Config | Database driver selection | `postgres`, `mysql` |
| `RELEASE_MODE` | Config | License enforcement | `true`/`false` |

### Custom Workflows

**If needed, create project-specific workflows**:

```
.github/workflows/
├── build-flask-backend.yml
├── build-go-backend.yml
├── build-webui.yml
├── [project-name]-special-ci.yml    # Project-specific
└── version-release.yml
```

### Project-Specific Notes

**This is a reference template for all PenguinTech projects**

All PenguinTech projects follow the same workflow structure and CI/CD patterns documented in this file. Use this as a reference guide when:

- Setting up new projects
- Troubleshooting CI/CD issues
- Adding new services
- Implementing security updates
- Optimizing build performance

Customization should be minimal and follow the patterns established in this template.

### Known Issues & Workarounds

**Document project-specific issues here**:

- **Issue**: [Description]
  - **Cause**: [Why it happens]
  - **Workaround**: [How to fix]
  - **Tracking**: [GitHub issue link if applicable]

### Performance Benchmarks

**Record baseline performance for your project**:

| Workflow | Avg Time | With Cache | Notes |
|----------|----------|-----------|-------|
| flask-backend | [time] | [time] | [Notes] |
| go-backend | [time] | [time] | [Notes] |
| webui | [time] | [time] | [Notes] |

### Support & Documentation

**Links to relevant resources**:

- **CI/CD Standards**: See `docs/STANDARDS.md` - CI/CD section
- **Security Scanning**: See `docs/STANDARDS.md` - Security standards
- **Development Guide**: See `CLAUDE.md` - Development workflow
- **Version Management**: See `.version` file specification above
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Docker Build Docs**: https://docs.docker.com/build/guide/

---

## Quick Reference Cards

### Checklist: Before Committing Code

```
Before EVERY commit, verify:

[ ] Linting passes
    - Python: flake8, black, isort
    - Go: golangci-lint
    - Node.js: eslint, prettier

[ ] Security checks pass
    - Python: bandit, safety check
    - Go: gosec, go mod audit
    - Node.js: npm audit

[ ] Tests pass locally
    - Unit tests complete successfully
    - No test failures or errors

[ ] Manual testing complete
    - Health check endpoints respond
    - Basic functionality works
    - Logs show expected output

[ ] No debug code left in
    - No console.log, print(), println! statements
    - No commented code blocks
    - No debug flags enabled

[ ] Configuration is correct
    - Environment variables correct
    - Database connections working
    - API endpoints accessible
```

### Checklist: After Pushing Code

```
After EVERY push, verify:

[ ] GitHub Actions workflow triggered
    - Check Actions tab shows workflow run
    - Verify it's running for your commit

[ ] Workflow completes successfully
    - All jobs pass (Lint, Test, Build, Security)
    - No failed steps
    - Images pushed to registry

[ ] Image tagged correctly
    - Check registry for correct tags
    - beta-<epoch> or alpha-<epoch> for code changes
    - vX.X.X-beta or vX.X.X-alpha for version changes

[ ] Pre-release created (if .version changed)
    - GitHub releases shows pre-release
    - Release notes auto-generated
    - Version matches .version file

[ ] No security vulnerabilities
    - Trivy scan completed
    - CodeQL scan completed
    - No critical/high severity issues
```

### Checklist: Updating .version

```
When bumping version:

[ ] Determine version type
    - Patch: Bug fixes (1.2.3 → 1.2.4)
    - Minor: New features (1.2.3 → 1.3.0)
    - Major: Breaking changes (1.2.3 → 2.0.0)

[ ] Update .version file
    - echo "X.Y.Z" > .version
    - Follow semantic versioning

[ ] Verify format
    - Format: X.Y.Z (no leading v, no build suffix)
    - Example: 1.2.3

[ ] Commit and push
    - git add .version
    - git commit -m "Bump version to X.Y.Z"
    - git push origin main

[ ] Verify pre-release created
    - Check GitHub Releases
    - Pre-release should appear within seconds
    - Release notes auto-generated

[ ] Tag release when ready
    - gh release edit vX.X.Z --prerelease=false
    - Updates all services to point to latest
```

### Debugging Failed Workflows

For detailed debugging procedures and troubleshooting steps, see **[WORKFLOWS-TROUBLESHOOTING.md](WORKFLOWS-TROUBLESHOOTING.md)**.

**Quick Steps**:
1. Check GitHub Actions logs for error messages
2. Identify failure type (lint, test, build, security)
3. Reproduce locally with same steps
4. Fix issue and test locally before committing
5. Verify fix in GitHub Actions

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-11 | Customized for Project Template: Three services (flask-backend, go-backend, webui), PenguinTech reference template |

---

**Last Updated**: December 11, 2025
**Template Version**: 1.0.0
**Project**: Project Template
**For Questions**: Refer to `docs/STANDARDS.md` or `CLAUDE.md`
