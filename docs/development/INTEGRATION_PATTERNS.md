# Common Integration Patterns

This document provides standard integration patterns used across Penguin Tech Inc projects. These patterns establish best practices for common development tasks including licensing, database access, API development, and monitoring.

## License-Gated Features

License-gated features enable feature availability based on the customer's license tier. This pattern is fundamental to the PenguinTech License Server integration and ensures enterprise functionality is properly restricted.

### Python Implementation

```python
# Python feature gating
from shared.licensing import license_client, requires_feature

@requires_feature("advanced_analytics")
def generate_advanced_report():
    """This feature requires professional+ license"""
    return advanced_analytics.generate_report()

# Startup validation
def initialize_application():
    client = license_client.get_client()
    validation = client.validate()
    if not validation.get("valid"):
        logger.error(f"License validation failed: {validation.get('message')}")
        sys.exit(1)

    logger.info(f"License valid for {validation['customer']} ({validation['tier']})")
    return validation
```

### Go Implementation

```go
// Go feature gating
package main

import (
    "log"
    "os"
    "your-project/internal/license"
)

func main() {
    client := license.NewClient(os.Getenv("LICENSE_KEY"), "your-product")

    validation, err := client.Validate()
    if err != nil || !validation.Valid {
        log.Fatal("License validation failed")
    }

    log.Printf("License valid for %s (%s)", validation.Customer, validation.Tier)

    // Check features
    if hasAdvanced, _ := client.CheckFeature("advanced_feature"); hasAdvanced {
        log.Println("Advanced features enabled")
    }
}
```

## Database Integration

Database integration patterns provide consistent approaches for data persistence across Python and Go applications.

### Python with PyDAL

PyDAL (Python Database Abstraction Layer) is the standard ORM for Python applications in this template. It provides database-agnostic interfaces with built-in validation and migration support.

```python
# Python with PyDAL
from pydal import DAL, Field

db = DAL('postgresql://user:pass@host/db')
db.define_table('users',
    Field('name', 'string', requires=IS_NOT_EMPTY()),
    Field('email', 'string', requires=IS_EMAIL()),
    migrate=True, fake_migrate=False)
```

Key features:
- Support for multiple database backends (PostgreSQL, MySQL, SQLite)
- Built-in field validators
- Automatic migrations
- Declarative table definitions

### Go with GORM

GORM (Go Object-Relational Mapping) provides type-safe database access for Go services with comprehensive query capabilities.

```go
// Go with GORM
import "gorm.io/gorm"

type User struct {
    ID    uint   `gorm:"primaryKey"`
    Name  string `gorm:"not null"`
    Email string `gorm:"uniqueIndex;not null"`
}
```

Key features:
- Struct-based model definitions
- Type-safe queries
- Automatic migrations
- Relationship support

## API Development

API patterns establish consistent approaches for building REST endpoints across different frameworks.

### Python with py4web

py4web is the standard web framework for Python applications, providing decorator-based routing and CORS support.

```python
# Python with py4web
from py4web import action, request, response
from py4web.utils.cors import CORS

@action('api/users', method=['GET', 'POST'])
@CORS()
def api_users():
    if request.method == 'GET':
        return {'users': db(db.users).select().as_list()}
    # Handle POST...
```

Key features:
- Decorator-based routing
- Built-in CORS support
- Request/response handling
- Database integration

### Go with Gin

Gin is a lightweight Go web framework providing high-performance routing and middleware support.

```go
// Go with Gin
func setupRoutes() *gin.Engine {
    r := gin.Default()
    r.Use(cors.Default())

    v1 := r.Group("/api/v1")
    {
        v1.GET("/users", getUsers)
        v1.POST("/users", createUser)
    }
    return r
}
```

Key features:
- Fast routing engine
- Middleware support
- CORS handling
- Request validation

## Monitoring Integration

Monitoring integration provides consistent approaches for metrics collection and exposure to Prometheus.

### Python Metrics

Python applications expose metrics using the prometheus_client library, enabling collection by Prometheus scrapers.

```python
# Python metrics
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@action('metrics')
def metrics():
    return generate_latest(), {'Content-Type': 'text/plain'}
```

Key features:
- Counter metrics for totals
- Histogram metrics for distributions
- Labels for dimensional data
- Metrics endpoint exposure

### Go Metrics

Go applications use the prometheus/client_golang library for metrics collection and exposition.

```go
// Go metrics
import "github.com/prometheus/client_golang/prometheus"

var (
    requestCount = prometheus.NewCounterVec(
        prometheus.CounterOpts{Name: "http_requests_total"},
        []string{"method", "endpoint"})
    requestDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{Name: "http_request_duration_seconds"},
        []string{"method", "endpoint"})
)
```

Key features:
- Strongly-typed metric definitions
- Vector metrics with labels
- Counter and histogram support
- Standard Prometheus format

## Pattern Usage Guidelines

- **License-Gated Features**: Always validate licenses at startup and gate premium functionality with the `@requires_feature` decorator (Python) or manual checks (Go)
- **Database Integration**: Use PyDAL for Python applications and GORM for Go services. Ensure all table definitions include appropriate validators and constraints
- **API Development**: Follow REST conventions with proper HTTP methods. Always include CORS support and request validation
- **Monitoring Integration**: Expose metrics on a `/metrics` endpoint. Include request counts and durations for all API endpoints

These patterns ensure consistency across the project ecosystem and facilitate operational visibility, security, and maintainability.
