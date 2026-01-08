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

## License & Legal

**License File**: `LICENSE.md` (located at project root)

**License Type**: Limited AGPL-3.0 with commercial use restrictions and Contributor Employer Exception

The `LICENSE.md` file is located at the project root following industry standards. This project uses a modified AGPL-3.0 license with additional exceptions for commercial use and special provisions for companies employing contributors.

- **License Server**: https://license.penguintech.io
- **Company Website**: www.penguintech.io
- **Support**: support@penguintech.io

---

**Current Version**: See `.version` file
**Last Updated**: 2025-12-18
**Maintained by**: Penguin Tech Inc
