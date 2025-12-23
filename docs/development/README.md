# Development Documentation

This directory contains detailed development practices, rules, and patterns for the project.

## Contents

- **[CRITICAL_RULES.md](CRITICAL_RULES.md)** - Mandatory development rules and workflows
  - Git workflow rules (never commit automatically, never push)
  - Local state management (.PLAN/.TODO files)
  - Dependency security requirements
  - Build & deployment requirements
  - Docker and GitHub Actions standards

- **[PERFORMANCE.md](PERFORMANCE.md)** - Performance optimization best practices
  - Python async/concurrent patterns and modern optimizations
  - Go performance patterns
  - Networking optimizations (eBPF/XDP, NUMA-aware)
  - Memory management and I/O operations

- **[INTEGRATION_PATTERNS.md](INTEGRATION_PATTERNS.md)** - Common integration code examples
  - License-gated features (Python/Go)
  - Database integration (PyDAL/GORM)
  - API development (py4web/Gin)
  - Monitoring integration (Prometheus)

## Related Documentation

- [Architecture Documentation](../architecture/) - System architecture and structure
- [STANDARDS.md](../STANDARDS.md) - Development standards and guidelines
- [WORKFLOWS.md](../WORKFLOWS.md) - Workflow and process documentation
