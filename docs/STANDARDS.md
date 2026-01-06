# Development Standards

This document consolidates all development standards, patterns, and requirements for the Nest project, built on Penguin Tech Inc template best practices.

---

## Language Selection Criteria

**Evaluate on a case-by-case basis which language to use for each project or service:**

### Python 3.13 (Default Choice)
**Use Python for most applications:**
- Web applications and REST APIs
- Business logic and data processing
- Integration services and connectors
- CRUD applications
- Admin panels and internal tools
- Low to moderate traffic applications (<10K req/sec)

**Advantages:**
- Rapid development and iteration
- Rich ecosystem of libraries
- Excellent for prototyping and MVPs
- Strong support for data processing
- Easy maintenance and debugging

### Go 1.23.x (Performance-Critical Only)
**Use Go ONLY for high-traffic, performance-critical applications:**
- Applications handling >10K requests/second
- Network-intensive services requiring low latency
- Services with latency requirements <10ms
- CPU-bound operations requiring maximum throughput
- Systems requiring minimal memory footprint
- Real-time processing pipelines

**Traffic Threshold Decision Matrix:**
| Requests/Second | Language Choice | Rationale |
|-----------------|-----------------|-----------|
| < 1K req/sec    | Python 3.13     | Development speed priority |
| 1K - 10K req/sec| Python 3.13     | Python can handle with optimization |
| 10K - 50K req/sec| Evaluate both  | Consider complexity vs performance needs |
| > 50K req/sec   | Go 1.23.x       | Performance becomes critical |

**Important Considerations:**
- Start with Python for faster iteration
- Profile and measure actual performance before switching
- Consider operational complexity of multi-language stack
- Go adds development overhead - only use when necessary

---

## Flask-Security-Too Integration

**MANDATORY for ALL Flask applications - provides comprehensive security framework**

### Core Features
- User authentication and session management
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Email confirmation and password reset
- Two-factor authentication (2FA)
- Token-based authentication for APIs
- Login tracking and session management

### Integration with PyDAL

Flask-Security-Too integrates with PyDAL for database operations:

```python
from flask import Flask
from flask_security import Security, auth_required, hash_password
from flask_security.datastore import DataStore, UserDataMixin, RoleDataMixin
from pydal import DAL, Field
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'super-secret')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT', 'salt')
app.config['SECURITY_REGISTERABLE'] = True
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'

# PyDAL database setup
db = DAL(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    pool_size=10,
    migrate=True
)

# Define user and role tables
db.define_table('auth_user',
    Field('email', 'string', requires=IS_EMAIL(), unique=True),
    Field('username', 'string', unique=True),
    Field('password', 'string'),
    Field('active', 'boolean', default=True),
    Field('fs_uniquifier', 'string', unique=True),
    Field('confirmed_at', 'datetime'),
    migrate=True
)

db.define_table('auth_role',
    Field('name', 'string', unique=True),
    Field('description', 'text'),
    migrate=True
)

db.define_table('auth_user_roles',
    Field('user_id', 'reference auth_user'),
    Field('role_id', 'reference auth_role'),
    migrate=True
)

# Custom PyDAL datastore for Flask-Security-Too
class PyDALUserDatastore(DataStore):
    def __init__(self, db, user_model, role_model):
        self.db = db
        self.user_model = user_model
        self.role_model = role_model

    def put(self, model):
        self.db.commit()
        return model

    def delete(self, model):
        self.db(self.user_model.id == model.id).delete()
        self.db.commit()

    def find_user(self, **kwargs):
        query = self.db(self.user_model)
        for key, value in kwargs.items():
            if hasattr(self.user_model, key):
                query = query(self.user_model[key] == value)
        row = query.select().first()
        return row

# Initialize Flask-Security-Too
user_datastore = PyDALUserDatastore(db, db.auth_user, db.auth_role)
security = Security(app, user_datastore)

# Protected route example
@app.route('/api/protected')
@auth_required()
def protected_endpoint():
    return {'message': 'Access granted', 'user': current_user.email}

# Admin-only route example
@app.route('/api/admin')
@auth_required()
@roles_required('admin')
def admin_endpoint():
    return {'message': 'Admin access granted'}
```

### SSO Integration (Enterprise Feature)

**ALWAYS license-gate SSO as an enterprise-only feature:**

```python
from shared.licensing import requires_feature
from flask_security import auth_required

@app.route('/auth/saml/login')
@requires_feature('sso_saml')
def saml_login():
    """SAML SSO login - enterprise feature"""
    # SAML authentication logic
    pass

@app.route('/auth/oauth/login')
@requires_feature('sso_oauth')
def oauth_login():
    """OAuth SSO login - enterprise feature"""
    # OAuth authentication logic
    pass
```

**SSO Configuration:**
```python
# Enterprise SSO features (license-gated)
if license_client.has_feature('sso_saml'):
    app.config['SECURITY_SAML_ENABLED'] = True
    app.config['SECURITY_SAML_IDP_METADATA_URL'] = os.getenv('SAML_IDP_METADATA_URL')

if license_client.has_feature('sso_oauth'):
    app.config['SECURITY_OAUTH_ENABLED'] = True
    app.config['SECURITY_OAUTH_PROVIDERS'] = {
        'google': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        },
        'azure': {
            'client_id': os.getenv('AZURE_CLIENT_ID'),
            'client_secret': os.getenv('AZURE_CLIENT_SECRET'),
        }
    }
```

### Environment Variables

Required environment variables for Flask-Security-Too:

```bash
# Flask-Security-Too core
SECRET_KEY=your-secret-key-here
SECURITY_PASSWORD_SALT=your-password-salt
SECURITY_REGISTERABLE=true
SECURITY_SEND_REGISTER_EMAIL=false

# SSO (Enterprise only - license-gated)
SAML_IDP_METADATA_URL=https://idp.example.com/metadata
GOOGLE_CLIENT_ID=google-oauth-client-id
GOOGLE_CLIENT_SECRET=google-oauth-client-secret
AZURE_CLIENT_ID=azure-oauth-client-id
AZURE_CLIENT_SECRET=azure-oauth-client-secret
```

---

## ReactJS Frontend Standards

**ALL frontend applications MUST use ReactJS**

### Project Structure

```
services/webui/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── components/      # Reusable components
│   ├── pages/           # Page components
│   ├── services/        # API client services
│   ├── hooks/           # Custom React hooks
│   ├── context/         # React context providers
│   ├── utils/           # Utility functions
│   ├── App.jsx
│   └── index.jsx
├── package.json
├── Dockerfile
└── .env
```

### Required Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "eslint": "^8.55.0",
    "prettier": "^3.1.0"
  }
}
```

### API Client Integration

**Create centralized API client for Flask backend:**

```javascript
// src/services/apiClient.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Important for session cookies
});

// Request interceptor for auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login on unauthorized
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Authentication Context

```javascript
// src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../services/apiClient';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated on mount
    const checkAuth = async () => {
      try {
        const response = await apiClient.get('/auth/user');
        setUser(response.data);
      } catch (error) {
        console.error('Not authenticated:', error);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (email, password) => {
    const response = await apiClient.post('/auth/login', { email, password });
    setUser(response.data.user);
    localStorage.setItem('authToken', response.data.token);
  };

  const logout = async () => {
    await apiClient.post('/auth/logout');
    setUser(null);
    localStorage.removeItem('authToken');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

### Component Standards

**Use functional components with hooks:**

```javascript
import React, { useState, useEffect } from 'react';
import { useUsers, useCreateUser } from '../hooks/useUsers';

export const UserList = () => {
  const { data: users, isLoading, error } = useUsers();
  const createUser = useCreateUser();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h2>Users</h2>
      <ul>
        {users.map(user => (
          <li key={user.id}>{user.name} - {user.email}</li>
        ))}
      </ul>
    </div>
  );
};
```

### Docker Configuration for React

```dockerfile
# services/webui/Dockerfile
FROM node:18-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## Database Standards

### PyDAL Configuration - MANDATORY for ALL Python Applications

ALL Python applications (web or non-web) MUST implement PyDAL database access.

**Note on PyDAL Augmentation:**
- PyDAL is the PRIMARY database abstraction layer
- Other libraries can augment PyDAL when absolutely necessary
- Any additional libraries must be justified and documented

### Go Database Requirements

When using Go for high-performance applications, MUST use a DAL supporting PostgreSQL and MySQL:

**Recommended Options:**
1. **GORM** (Preferred)
   - Full-featured ORM
   - Supports PostgreSQL, MySQL, SQLite, SQL Server
   - Active maintenance and large community
   - Auto migrations and associations

2. **sqlx** (Alternative)
   - Lightweight extension of database/sql
   - Supports PostgreSQL, MySQL, SQLite
   - More control, less abstraction
   - Good for performance-critical scenarios

**Example GORM Implementation:**
```go
package main

import (
    "os"
    "gorm.io/driver/postgres"
    "gorm.io/driver/mysql"
    "gorm.io/gorm"
)

func initDB() (*gorm.DB, error) {
    dbType := os.Getenv("DB_TYPE") // "postgres" or "mysql"
    dsn := os.Getenv("DATABASE_URL")

    var dialector gorm.Dialector
    switch dbType {
    case "mysql":
        dialector = mysql.Open(dsn)
    default: // postgres
        dialector = postgres.Open(dsn)
    }

    db, err := gorm.Open(dialector, &gorm.Config{})
    return db, err
}
```

#### Environment Variables

Applications MUST accept these Docker environment variables:
- `DB_TYPE`: Database type (postgresql, mysql, sqlite, mssql, oracle, etc.)
- `DB_HOST`: Database host/IP address
- `DB_PORT`: Database port (default depends on DB_TYPE)
- `DB_NAME`: Database name
- `DB_USER`: Database username
- `DB_PASS`: Database password
- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_RETRIES`: Maximum connection retry attempts (default: 5)
- `DB_RETRY_DELAY`: Delay between retry attempts in seconds (default: 5)

#### Database Connection Requirements

1. **Wait for Database Initialization**: Application MUST wait for database to be ready
   - Implement retry logic with exponential backoff
   - Maximum retry attempts configurable via `DB_MAX_RETRIES`
   - Log each connection attempt for debugging
   - Fail gracefully with clear error messages

2. **Connection Pooling**: MUST use PyDAL's built-in connection pooling
   - Configure pool size via `DB_POOL_SIZE` environment variable
   - Implement proper connection lifecycle management
   - Handle connection timeouts and stale connections
   - Monitor pool utilization via metrics

3. **Database URI Construction**: Build connection string from environment variables
   ```python
   db_uri = f"{DB_TYPE}://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
   ```

#### Thread Safety Requirements

**PyDAL MUST be used in a thread-safe manner:**

1. **Thread-local connections**: Each thread MUST have its own DAL instance
   - NEVER share a single DAL instance across multiple threads
   - Use thread-local storage (threading.local()) for per-thread DAL instances
   - Connection pooling handles multi-threaded access automatically

2. **Implementation Pattern for Threading:**
   ```python
   import threading
   from pydal import DAL

   # Thread-local storage for DAL instances
   thread_local = threading.local()

   def get_thread_db():
       """Get thread-local database connection"""
       if not hasattr(thread_local, 'db'):
           thread_local.db = DAL(
               db_uri,
               pool_size=10,
               migrate_enabled=True,
               check_reserved=['all'],
               lazy_tables=True
           )
       return thread_local.db

   # Usage in threaded context
   def worker_function():
       db = get_thread_db()  # Each thread gets its own connection
       # Perform database operations...
   ```

3. **Flask/WSGI Applications**: Flask already handles thread-local contexts
   ```python
   from flask import Flask, g

   app = Flask(__name__)

   def get_db():
       """Get database connection for current request context"""
       if 'db' not in g:
           g.db = DAL(db_uri, pool_size=10)
       return g.db

   @app.teardown_appcontext
   def close_db(error):
       """Close database connection after request"""
       db = g.pop('db', None)
       if db is not None:
           db.close()
   ```

---

## Protocol Support

**ALL applications MUST support multiple communication protocols:**

### Required Protocol Support

1. **REST API**: RESTful HTTP endpoints (GET, POST, PUT, DELETE, PATCH)
   - JSON request/response format
   - Proper HTTP status codes
   - Resource-based URL design

2. **gRPC**: High-performance RPC protocol
   - Protocol Buffers for message serialization
   - Bi-directional streaming support
   - Service definitions in .proto files
   - Health checking via gRPC health protocol

3. **HTTP/1.1**: Standard HTTP protocol support
   - Keep-alive connections
   - Chunked transfer encoding
   - Compression (gzip, deflate)

4. **HTTP/2**: Modern HTTP protocol
   - Multiplexing multiple requests over single connection
   - Header compression (HPACK)
   - Stream prioritization

5. **HTTP/3 (QUIC)**: Next-generation HTTP protocol
   - UDP-based transport with TLS 1.3
   - Zero round-trip time (0-RTT) connection establishment
   - Built-in encryption

### Protocol Configuration via Environment Variables

Applications must accept these environment variables:
- `HTTP1_ENABLED`: Enable HTTP/1.1 (default: true)
- `HTTP2_ENABLED`: Enable HTTP/2 (default: true)
- `HTTP3_ENABLED`: Enable HTTP/3/QUIC (default: false)
- `GRPC_ENABLED`: Enable gRPC (default: true)
- `HTTP_PORT`: HTTP/REST API port (default: 8080)
- `GRPC_PORT`: gRPC port (default: 50051)
- `METRICS_PORT`: Prometheus metrics port (default: 9090)

---

## API Versioning

**ALL REST APIs MUST use versioning in the URL path**

### URL Structure

**Required Format:** `/api/v{major}/endpoint`

**Examples:**
- `/api/v1/users` - User management
- `/api/v1/auth/login` - Authentication
- `/api/v1/organizations` - Organizations
- `/api/v2/analytics` - Version 2 of analytics endpoint

**Key Rules:**
1. **Always include version prefix** in URL path - NEVER use query parameters for versioning
2. **Semantic versioning** for API versions: `v1`, `v2`, `v3`, etc.
3. **Major version only** in URL - minor/patch versions are NOT in the URL
4. **Consistent prefix** across all endpoints in a service
5. **Version-specific** sub-resources: `/api/v1/users/{id}/profile` not `/api/v1/users/profile/{id}`

### Version Lifecycle

**Version Strategy:**
- **Current Version**: Active development and fully supported
- **Previous Version (N-1)**: Supported with bug fixes and security patches
- **Older Versions (N-2+)**: Deprecated with deprecation warning headers

---

## Performance Best Practices

**ALWAYS prioritize performance and stability through modern concurrency patterns**

### Python Performance Requirements

#### Dataclasses with Slots - MANDATORY

**ALL data structures MUST use dataclasses with slots for memory efficiency:**

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass(slots=True, frozen=True)
class User:
    """User model with slots for 30-50% memory reduction"""
    id: int
    name: str
    email: str
    created_at: str
    metadata: dict = field(default_factory=dict)
```

**Benefits of Slots:**
- 30-50% less memory per instance
- Faster attribute access
- Better type safety with type hints
- Immutability with `frozen=True`

#### Type Hints - MANDATORY

**Comprehensive type hints are REQUIRED for all Python code:**

```python
from typing import Optional, List, Dict
from collections.abc import AsyncIterator

async def process_users(
    user_ids: List[int],
    batch_size: int = 100,
    callback: Optional[Callable[[User], None]] = None
) -> Dict[int, User]:
    """Process users with full type hints"""
    results: Dict[int, User] = {}
    for user_id in user_ids:
        user = await fetch_user(user_id)
        results[user_id] = user
        if callback:
            callback(user)
    return results
```

### Go Performance Requirements
- **Goroutines**: Leverage goroutines and channels for concurrent operations
- **Sync primitives**: Use sync.Pool, sync.Map for concurrent data structures
- **Context**: Proper context propagation for cancellation and timeouts

---

## High-Performance Networking

**Evaluate on a case-by-case basis for network-intensive applications**

### When to Consider XDP/AF_XDP

Only evaluate XDP (eXpress Data Path) and AF_XDP for applications with extreme network requirements:

**Traffic Thresholds:**
- Standard applications: Regular socket programming (most cases)
- High traffic (>100K packets/sec): Consider XDP/AF_XDP
- Extreme traffic (>1M packets/sec): XDP/AF_XDP strongly recommended

### XDP (eXpress Data Path)

**Kernel-level packet processing:**
- Processes packets at the earliest point in networking stack
- Bypass most of kernel networking code
- Can drop, redirect, or pass packets
- Ideal for DDoS mitigation, load balancing, packet filtering

### AF_XDP (Address Family XDP)

**Zero-copy socket for user-space packet processing:**
- Bypass kernel networking stack entirely
- Direct packet access from NIC to user-space
- Lowest latency possible for packet processing
- More flexible than kernel XDP

### Decision Matrix: Networking Implementation

| Packets/Sec | Technology | Language | Justification |
|-------------|------------|----------|---------------|
| < 10K       | Standard sockets | Python 3.13 | Regular networking sufficient |
| 10K - 100K  | Optimized sockets | Python/Go | Standard with optimization |
| 100K - 500K | Consider XDP | Go + XDP | High performance needed |
| > 500K      | XDP/AF_XDP required | Go + AF_XDP | Extreme performance critical |

---

## Microservices Architecture

**ALWAYS use microservices architecture for application development**

### Three-Container Architecture

This template provides three base containers representing the core footprints:

| Container | Technology | Purpose | When to Use |
|-----------|------------|---------|-------------|
| **flask-backend** | Flask + PyDAL | Standard APIs, auth, CRUD | <10K req/sec, business logic |
| **go-backend** | Go + XDP/AF_XDP | High-performance networking | >10K req/sec, <10ms latency |
| **webui** | Node.js + React | Frontend shell | All frontend applications |

### Container Details

1. **WebUI Container** (Node.js + React)
   - Express server proxies API calls to backends
   - React SPA with role-based navigation
   - Elder-style collapsible sidebar
   - WaddlePerf-style tab navigation
   - Gold (amber-400) text theme

2. **Flask Backend** (Flask + PyDAL)
   - JWT authentication with bcrypt
   - User management CRUD (Admin only)
   - Role-based access: Admin, Maintainer, Viewer
   - PyDAL for multi-database support
   - Health check endpoints

3. **Go Backend** (Go + XDP/AF_XDP)
   - XDP for kernel-level packet processing
   - AF_XDP for zero-copy user-space I/O
   - NUMA-aware memory allocation
   - Memory slot pools for packet buffers
   - Prometheus metrics

4. **Connector Container** (placeholder)
   - External system integration
   - Background job processing

### Default Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access: user CRUD, settings, all features |
| **Maintainer** | Read/write access to resources, no user management |
| **Viewer** | Read-only access to resources |

---

## Docker Standards

### Build Standards

**All builds MUST be executed within Docker containers:**

```bash
# Go builds (using debian-slim)
docker run --rm -v $(pwd):/app -w /app golang:1.23-slim go build -o bin/app

# Python builds (using debian-slim)
docker run --rm -v $(pwd):/app -w /app python:3.13-slim pip install -r requirements.txt
```

**Use multi-stage builds with debian-slim:**
```dockerfile
FROM golang:1.23-slim AS builder
FROM debian:stable-slim AS runtime

FROM python:3.13-slim AS builder
FROM debian:stable-slim AS runtime
```

### Docker Compose Standards

**ALWAYS create docker-compose.dev.yml for local development**

**Prefer Docker networks over host ports:**
- Minimize host port exposure
- Only expose ports for developer access
- Use named Docker networks for service-to-service communication

---

## Testing Requirements

### Unit Testing

**All applications MUST have comprehensive unit tests:**

- **Network isolation**: Unit tests must NOT require external network connections
- **No external dependencies**: Cannot reach databases, APIs, or external services
- **Use mocks/stubs**: Mock all external dependencies and I/O operations
- **KISS principle**: Keep unit tests simple, focused, and fast
- **Test isolation**: Each test should be independent and repeatable
- **Fast execution**: Unit tests should complete in milliseconds

### Integration Testing

- Test component interactions
- Use test databases and services
- Verify API contracts
- Test authentication and authorization

### End-to-End Testing

- Test critical user workflows
- Use staging environment
- Verify full system integration

### Performance Testing

- Benchmark critical operations
- Load testing for scalability
- Regression testing for performance

---

## Security Standards

### Input Validation

- ALL inputs MUST have appropriate validators
- Use framework-native validation (PyDAL validators, Go libraries)
- Implement XSS and SQL injection prevention
- Server-side validation for all client input
- CSRF protection using framework native features

### Authentication & Authorization

- Multi-factor authentication support
- Role-based access control (RBAC)
- API key management with rotation
- JWT token validation with proper expiration
- Session management with secure cookies

### TLS/Encryption

- **TLS enforcement**: TLS 1.2 minimum, prefer TLS 1.3
- **Connection security**: Use HTTPS where possible
- **Modern protocols**: HTTP3/QUIC for high-performance
- **Standard security**: JWT, MFA, mTLS where applicable
- **Enterprise SSO**: SAML/OAuth2 as enterprise features

### Dependency Security

- **ALWAYS check for Dependabot alerts** before commits
- **Monitor vulnerabilities** via Socket.dev
- **Mandatory security scanning** before dependency changes
- **Fix all security alerts immediately** - no commits with outstanding vulnerabilities
- **Version pinning**: Exact versions for security-critical dependencies

---

## Documentation Standards

### README.md Standards

**ALWAYS include build status badges:**
- CI/CD pipeline status (GitHub Actions)
- Test coverage status (Codecov)
- Go Report Card (for Go projects)
- Version badge
- License badge (Limited AGPL3)

**ALWAYS include catchy ASCII art** below badges

**Company homepage**: Point to **www.penguintech.io**

### CLAUDE.md File Management

- **Maximum**: 35,000 characters
- **High-level approach**: Reference detailed docs
- **Documentation strategy**: Create detailed docs in `docs/` folder
- **Keep focused**: Critical context and workflow instructions only

### API Documentation

- Comprehensive endpoint documentation
- Request/response examples
- Error codes and handling
- Authentication requirements
- Rate limiting information

### Architecture Documentation

- System architecture diagrams
- Component interaction patterns
- Data flow documentation
- Decision records (ADRs)

---

## Web UI Design Standards

**ALL ReactJS frontend applications MUST follow these design patterns:**

### Design Philosophy

- **Dark Theme Default**: Use dark backgrounds with light text for reduced eye strain
- **Consistent Spacing**: Use standardized spacing scale (Tailwind's spacing utilities)
- **Smooth Transitions**: Apply `transition-colors` or `transition-all 0.2s` for state changes
- **Subtle Gradients**: Use gradient accents sparingly for modern aesthetic
- **Responsive Design**: Mobile-first approach with breakpoint-based layouts

### Color Palette (Dark Theme)

**CSS Variables (Required):**
```css
:root {
  /* Background colors */
  --bg-primary: #0f172a;      /* slate-900 - main background */
  --bg-secondary: #1e293b;    /* slate-800 - sidebar/cards */
  --bg-tertiary: #334155;     /* slate-700 - hover states */

  /* Text colors - Gold default */
  --text-primary: #fbbf24;    /* amber-400 - headings, primary text */
  --text-secondary: #f59e0b;  /* amber-500 - body text */
  --text-muted: #d97706;      /* amber-600 - secondary/muted text */
  --text-light: #fef3c7;      /* amber-100 - high contrast text */

  /* Accent colors (sky-blue for interactive elements) */
  --primary-400: #38bdf8;
  --primary-500: #0ea5e9;
  --primary-600: #0284c7;
  --primary-700: #0369a1;

  /* Border colors */
  --border-color: #334155;    /* slate-700 */

  /* Admin/Warning accent */
  --warning-color: #eab308;   /* yellow-500 */
}
```

---

## WaddleAI Integration

**Optional AI capabilities - integrate only when AI features are required**

### When to Use WaddleAI

Consider WaddleAI integration for projects requiring:
- Natural language processing (NLP)
- Machine learning model inference
- AI-powered features and automation
- Intelligent data analysis
- Chatbots and conversational interfaces
- Document understanding and extraction
- Predictive analytics

### License-Gating AI Features

**ALWAYS make AI features enterprise-only:**

```python
# License configuration
AI_FEATURES = {
    'ai_analysis': 'professional',      # Professional tier+
    'ai_generation': 'professional',    # Professional tier+
    'ai_training': 'enterprise',        # Enterprise tier only
    'ai_custom_models': 'enterprise'    # Enterprise tier only
}

# Feature checking
from shared.licensing import license_client

def check_ai_features():
    """Check available AI features based on license"""
    features = {}
    for feature, required_tier in AI_FEATURES.items():
        features[feature] = license_client.has_feature(feature)
    return features
```

---

## Nest-Specific Standards

### Networking Stack

The Nest project specializes in high-performance networking and infrastructure:

**Performance Requirements:**
- Optimize for <10ms latency where possible
- Support >10K concurrent connections
- Handle high-volume packet processing efficiently
- Implement monitoring for network metrics
- Profile and optimize hot paths regularly

**Networking Patterns:**
- Use Go for networking components requiring extreme performance
- Python for network control planes and APIs
- React for UI/monitoring dashboards
- XDP/AF_XDP for packet processing when needed

**Integration Points:**
- Monitor HTTP/REST API performance
- Track gRPC service metrics
- Collect network performance baselines
- Alert on latency degradation

---

**Last Updated**: 2025-12-18
**Maintained by**: Penguin Tech Inc
**Template Version**: 1.5.0
