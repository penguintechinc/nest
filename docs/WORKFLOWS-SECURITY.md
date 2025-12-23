# CI/CD Workflows - Security Scanning

## Overview

Each workflow includes multiple security checks:

1. **Dependency Scanning**: Language-specific audits for vulnerable packages
2. **Code Analysis**: Language-specific linting and security rules
3. **Container Scanning**: Trivy vulnerability scanner for Docker images
4. **Secret Scanning**: Detect accidentally committed secrets (GitHub native)

## Language-Specific Security Checks

### Python Services (Flask)

**Bandit** - Scans for common Python security issues:

```yaml
- name: Run bandit security check
  working-directory: services/flask-backend
  run: bandit -r app -ll
```

Fails on `HIGH` or `CRITICAL` severity only (allows `MEDIUM` and `LOW`).

**Additional Checks**:
- Linting: `flake8`, `black`, `isort`
- Type checking: `mypy` for type safety
- Dependency audit: `safety check` for vulnerable packages

### Go Services

**gosec** - Scans for Go security issues:

```yaml
- name: Run gosec security scanner
  uses: securecodewarrior/github-action-gosec@master
  with:
    args: '-severity high -confidence medium ./...'
```

Fails on `HIGH` or `CRITICAL` severity.

**Additional Checks**:
- Linting: `golangci-lint` (includes gosec rules)
- Dependency audit: `go mod audit`

### Node.js Services (React, WebUI)

**npm audit** - Scans npm dependencies:

```yaml
- name: Run npm audit
  working-directory: services/webui
  run: npm audit --audit-level=high
```

Fails on `HIGH` or `CRITICAL` severity vulnerabilities.

**Additional Checks**:
- Linting: `eslint`, `prettier`
- Dependency tracking: Dependabot alerts

## Container Scanning

**Trivy** - Scans built Docker images:

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'
```

- Scans for known vulnerabilities in base image and installed packages
- Results uploaded to GitHub Security tab
- Does not fail build (allows informational scanning)

## CodeQL Analysis

GitHub's CodeQL performs automatic code analysis:

- Detects common code patterns that could be exploited
- Runs on all push events to main/develop
- Results visible in Security tab → Code scanning alerts
- Fails if critical issues found (configurable)

## Security Scanning Order

Best practice execution order:

1. **Linting** (first - cheapest, fast feedback)
   - `flake8`, `black`, `isort` (Python)
   - `golangci-lint` (Go)
   - `eslint`, `prettier` (Node.js)

2. **Dependency Audits** (second - catch vulnerable packages)
   - `bandit`, `safety check` (Python)
   - `gosec`, `go mod audit` (Go)
   - `npm audit` (Node.js)

3. **Unit Tests** (third - verify functionality)
   - `pytest` (Python)
   - `go test` (Go)
   - `jest` (Node.js)

4. **Build** (fourth - create artifacts)
   - Docker image build with multi-arch support

5. **Container Scan** (fifth - scan final image)
   - Trivy vulnerability scanner

## Security Alert Response

If a security check fails:

1. **Do not commit** if security vulnerabilities are found
2. **Fix vulnerabilities immediately**:
   - Update vulnerable dependencies
   - Fix code issues flagged by security scanners
   - Address container vulnerabilities
3. **Re-run checks** locally before commit:
   - `cd services/[service] && npm run lint` or equivalent
   - `cd services/[service] && npm run security` or equivalent
4. **Document fixes** in commit message if security-related
