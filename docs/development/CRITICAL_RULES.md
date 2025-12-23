# Critical Development Rules

These are mandatory rules that govern all development activities in this project. Adherence to these rules ensures code quality, security, reliability, and consistency across the codebase. Violations of these critical rules can compromise project integrity and must be avoided at all costs.

## Git Workflow

- **NEVER commit automatically** unless explicitly requested by the user
- **NEVER push to remote repositories** under any circumstances
- **ONLY commit when explicitly asked** - never assume commit permission
- Always use feature branches for development
- Require pull request reviews for main branch
- Automated testing must pass before merge

## Local State Management (Crash Recovery)

- **ALWAYS maintain local .PLAN and .TODO files** for crash recovery
- **Keep .PLAN file updated** with current implementation plans and progress
- **Keep .TODO file updated** with task lists and completion status
- **Update these files in real-time** as work progresses to prevent data loss
- **Add to .gitignore**: Both .PLAN and .TODO files must be in .gitignore as they can expose sensitive information
- **File format**: Use simple text format for easy recovery and readability
- **Automatic recovery**: Upon restart, check for existing .PLAN and .TODO files to resume work

## Dependency Security Requirements

- **ALWAYS check for Dependabot alerts** before every commit using GitHub CLI or API
- **Monitor vulnerabilities via Socket.dev** for all Python, Go, and Node.js dependencies
- **Mandatory security scanning** before any dependency changes are committed
- **Fix all security alerts immediately** - no commits with outstanding vulnerabilities
- **Automated dependency updates**: Use tools like Dependabot, Renovate, or custom scripts
- **Version pinning strategy**: Use exact versions for security-critical dependencies
- **Regular security audits**:
  - `npm audit` for Node.js projects
  - `go mod audit` or equivalent tools for Go projects
  - `safety check` or equivalent for Python projects
- **Vulnerability response process**:
  1. Identify affected packages and severity
  2. Update to patched versions immediately
  3. Test updated dependencies thoroughly
  4. Document security fixes in commit messages
  5. Verify no new vulnerabilities introduced

## Build & Deployment Requirements

- **NEVER mark tasks as completed until successful build verification**
- All Go and Python builds MUST be executed within Docker containers for consistency
- Use containerized builds for both local development and CI/CD pipelines
- Build failures must be resolved before task completion
- Container builds ensure environment consistency across development and production

## Docker Build Standards

### Go Builds

```bash
# Go builds within containers (using debian-slim)
docker run --rm -v $(pwd):/app -w /app golang:1.23-slim go build -o bin/app
docker build -t app:latest .
```

### Python Builds

```bash
# Python builds within containers (using debian-slim)
# Use Python 3.12 for py4web applications due to py4web compatibility issues with 3.13
docker run --rm -v $(pwd):/app -w /app python:3.12-slim pip install -r requirements.txt
docker build -t web:latest .
```

### Multi-Stage Builds

```dockerfile
# Use multi-stage builds with debian-slim for optimized production images
FROM golang:1.23-slim AS builder
FROM debian:stable-slim AS runtime

FROM python:3.12-slim AS builder
FROM debian:stable-slim AS runtime
```

## GitHub Actions Multi-Arch Build Strategy

```yaml
# Single workflow with multi-arch builds for each container
name: Build Containers
jobs:
  build-app:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v4
        with:
          platforms: linux/amd64,linux/arm64
          context: ./apps/app
          file: ./apps/app/Dockerfile

  build-manager:
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v4
        with:
          platforms: linux/amd64,linux/arm64
          context: ./apps/manager
          file: ./apps/manager/Dockerfile

# Separate parallel workflows for each container type (app, manager, etc.)
# Each workflow builds multi-arch for that specific container
# Minimize build time through parallel container builds and caching
```

## Code Quality

- Follow language-specific style guides
- Comprehensive test coverage (80%+ target)
- No hardcoded secrets or credentials
- Proper error handling and logging
- Security-first development approach

---

**Last Updated**: 2025-12-23
**Maintained by**: Penguin Tech Inc
