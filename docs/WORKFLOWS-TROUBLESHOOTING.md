# CI/CD Workflows - Troubleshooting Guide

## Troubleshooting

### Workflow Execution Issues

#### Workflow Doesn't Trigger

**Problem**: Pushed code but workflow didn't run

**Causes & Solutions**:

1. **Branch not configured**:
   - Check `.version` path is in path filter
   - Verify branch is `main` or `develop`
   - Workflow only triggers on configured branches

2. **Path filter excludes change**:
   - Path filters prevent workflow from running
   - Verify file changed matches path pattern:
     ```yaml
     paths:
       - 'services/myservice/**'  # Only matches files under this path
     ```
   - If file is outside path, workflow won't trigger

3. **Syntax error in workflow file**:
   - GitHub will show error in Actions tab
   - Check workflow YAML syntax with online validator
   - Common: Missing quotes, incorrect indentation

**Fix**:
```bash
# Verify workflow file syntax
curl -X POST https://api.github.com/repos/[owner]/[repo]/actions/workflows/build-service.yml/validate \
  -H "Authorization: token $GITHUB_TOKEN" \
  -d @build-service.yml

# Or use local validator
yamllint .github/workflows/build-service.yml
```

#### Build Fails Unexpectedly

**Problem**: Build passed locally but fails in GitHub Actions

**Common Causes**:

1. **Environment variable missing**:
   - GitHub Actions doesn't have local environment vars
   - Set in workflow or in GitHub repository secrets
   - Access with `${{ secrets.VAR_NAME }}`

2. **Permissions missing**:
   - Token doesn't have required permissions
   - Check `permissions:` section in workflow
   - May need to adjust GitHub Actions token permissions

3. **Dependency version mismatch**:
   - Local: Specific version of Go/Python/Node installed
   - GitHub: May use different version
   - Use `setup-go@v5` / `setup-python@v5` with specific versions

4. **File not found in container**:
   - Dockerfile copies wrong path
   - Check working directory in Dockerfile
   - Verify COPY commands use correct paths

**Debug steps**:
```bash
# View full build output
# GitHub Actions → [Workflow] → [Run] → Click job to expand

# Test in container locally
docker run -it my-service:test /bin/bash
# Verify files exist, permissions correct, etc.

# Check environment variables
echo $PATH
echo $GOROOT
env | grep -i python
```

#### Security Scan Failures

**Problem**: Bandit/gosec/npm audit fails the build

**Solutions**:

1. **Vulnerable dependency found**:
   ```bash
   # Update dependencies
   pip install --upgrade [package]  # Python
   go get -u ./...                  # Go
   npm update                       # Node.js

   # Or explicitly set version
   pip install [package]==X.Y.Z
   go get [package]@vX.Y.Z
   npm install [package]@X.Y.Z
   ```

2. **False positive/acceptable risk**:
   ```bash
   # Suppress specific check (use sparingly)
   # Python
   bandit -r app -ll --exclude B101,B601

   # Go
   gosec -no-tests -exclude=G104 ./...

   # Node.js - Usually no suppression, fix dependencies
   ```

3. **Check what's failing**:
   ```bash
   # Run locally to see details
   cd services/[service]
   npm audit             # Shows all vulnerabilities
   bandit -r app -v      # Verbose output
   gosec -fmt=json ./... # JSON output for parsing
   ```

### Container Build Issues

#### Docker Build Fails

**Problem**: `docker build` fails locally

**Common errors**:

1. **Base image not found**:
   ```dockerfile
   FROM python:3.13-slim  # OK
   FROM python:3.13      # Not slim (larger image)
   FROM pyrhon:3.13      # Typo!
   ```
   **Solution**: Use valid image names, prefer slim variants

2. **Dependencies not installed**:
   ```dockerfile
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . /app              # Must copy after install
   WORKDIR /app
   CMD ["python", "app.py"]
   ```

3. **File not found during COPY**:
   ```dockerfile
   COPY setup.py /app/  # File doesn't exist = build fails
   ```
   **Solution**: Check file exists before COPY, verify paths

4. **Port binding conflicts**:
   ```yaml
   # docker-compose.yml
   ports:
     - "5000:5000"  # Host:Container - if 5000 in use, fails
   ```
   **Solution**: `docker-compose down` or change port

**Debug**:
```bash
# Build with verbose output
docker build --progress=plain --no-cache -t test . 2>&1 | tail -50

# Inspect partially built image
docker build -t test . || docker run -it [image-id] /bin/bash
```

#### Image Size Too Large

**Problem**: Docker image > 500MB (should be 100-300MB)

**Solutions**:

1. **Use slim base images**:
   ```dockerfile
   FROM python:3.13-slim     # ~150MB
   FROM python:3.13          # ~900MB
   FROM debian:12-slim       # ~80MB
   FROM debian:12            # ~100MB
   ```

2. **Clean up package managers**:
   ```dockerfile
   RUN apt-get update && apt-get install -y curl \
       && rm -rf /var/lib/apt/lists/*  # Remove apt cache
   ```

3. **Multi-stage builds**:
   ```dockerfile
   FROM python:3.13-slim as builder
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   FROM python:3.13-slim
   COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
   ```

4. **Don't include unnecessary files**:
   ```
   .dockerignore:
   __pycache__
   .pytest_cache
   .git
   *.pyc
   node_modules
   ```

### Version & Naming Issues

#### Wrong Tag Created

**Problem**: Image tagged as `latest` instead of `vX.X.X`

**Cause**: Release workflow metadata logic

**Solutions**:

1. **Check branch**: Must be on main branch for `beta-` tags
   ```bash
   git branch -a
   git checkout main
   ```

2. **Check .version**: Must match semver format `X.Y.Z`
   ```bash
   cat .version
   echo "1.2.3" > .version
   ```

3. **Verify release exists**: Pre-release already created
   ```bash
   gh release list
   gh release view vX.X.X
   ```

4. **Manually tag if needed**:
   ```bash
   git tag -a vX.X.X -m "Release X.X.X"
   git push origin vX.X.X
   ```

#### Pre-Release Not Created

**Problem**: Updated `.version` but pre-release not created

**Causes**:

1. **On wrong branch**: version-release.yml only triggers on `main`
   ```bash
   git checkout main
   echo "1.2.4" > .version
   git add .version && git commit -m "Bump version" && git push
   ```

2. **Version is 0.0.0**: Skipped intentionally
   ```bash
   echo "1.0.0" > .version  # Use real version
   ```

3. **Release already exists**: Not created again
   ```bash
   gh release delete vX.X.X  # Delete if needed
   git push origin --delete vX.X.X  # Delete tag
   # Then update .version and commit again
   ```

4. **Workflow failed**: Check GitHub Actions logs
   ```bash
   # View workflow runs
   gh run list --workflow=version-release.yml

   # View failed run details
   gh run view [run-id] --log
   ```

### Permission & Authentication Issues

#### Cannot Push to Registry

**Problem**: Build fails with authentication error

**Cause**: GITHUB_TOKEN doesn't have permission or expired

**Solution**:

1. **Check repository settings**:
   - Settings → Actions → General
   - "Workflow permissions" should be "Read and write permissions"

2. **Verify authentication step**:
   ```yaml
   - name: Log in to Container Registry
     uses: docker/login-action@v3
     with:
       registry: ghcr.io
       username: ${{ github.actor }}
       password: ${{ secrets.GITHUB_TOKEN }}  # Should work with runner token
   ```

3. **Test token manually**:
   ```bash
   echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
   ```

#### Release Creation Fails

**Problem**: "Failed to create release"

**Cause**: Missing permissions or token issue

**Solution**:

1. **Check permissions**:
   ```yaml
   permissions:
     contents: write  # Required for release creation
   ```

2. **Verify GITHUB_TOKEN is available**:
   ```bash
   # This should work in workflow
   env:
     GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```

3. **Check release doesn't already exist**:
   ```bash
   gh release view "vX.X.X"
   ```

### Slow Builds

#### Build Takes Too Long

**Problem**: Workflow takes 20+ minutes

**Solutions** (in order):

1. **Check path filters** (most common):
   - Missing `.version` causes unnecessary rebuilds
   - Verify only needed paths trigger workflow

2. **Check cache is working**:
   ```yaml
   cache-from: type=gha
   cache-to: type=gha,mode=max
   ```
   - First build slow (no cache) - expected
   - Subsequent builds use cache (faster) - expected

3. **Optimize Dockerfile**:
   - Move expensive operations after stable layers
   - Remove unnecessary dependencies
   - Use multi-stage builds

4. **Check test suite**:
   - Long-running tests block build job
   - Consider parallelizing tests across jobs
   - Only run unit tests (not integration tests)

5. **Check dependencies**:
   - Large dependency sets slow pip/npm/go install
   - Review requirements for unused packages
   - Pin specific versions to avoid lengthy resolution

---

## Debugging Checklists

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

### Checklist: Debugging Failed Workflow

```
When workflow fails:

[ ] Check GitHub Actions logs
    - Workflow run → Click failed job
    - Expand step to see error message
    - Look for "Error:" or "FAILED" keywords

[ ] Identify failure type
    - Lint failure? → Run linters locally
    - Test failure? → Run tests locally
    - Build failure? → Run docker build locally
    - Push failure? → Check permissions

[ ] Reproduce locally
    - Clone latest main branch
    - Run same steps as workflow
    - Identify root cause

[ ] Fix the issue
    - Code changes, dependency updates, etc.
    - Test fix locally
    - Commit and push

[ ] Verify fix
    - Watch GitHub Actions run
    - Confirm all jobs pass
    - Verify images tagged correctly
```

---

**Last Updated**: December 11, 2025
**For complete CI/CD documentation**: See `docs/WORKFLOWS.md`
