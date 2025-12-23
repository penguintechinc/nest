# Development Standards

This document consolidates core development standards for projects using this template. For detailed information on specific topics, refer to the linked documentation files below.

## Documentation Index

This file contains unique standards not covered elsewhere. For comprehensive coverage of specific topics, see:

- **[APPLICATION_ARCHITECTURE.md](architecture/APPLICATION_ARCHITECTURE.md)** - Microservices architecture, Docker standards, protocol support, web frameworks, logging & monitoring
- **[PERFORMANCE.md](development/PERFORMANCE.md)** - Performance best practices, concurrency patterns, high-performance networking, optimization strategies
- **[INTEGRATION_PATTERNS.md](development/INTEGRATION_PATTERNS.md)** - Flask-Security-Too integration, WaddleAI integration, common integration patterns
- **[CRITICAL_RULES.md](development/CRITICAL_RULES.md)** - Git workflow, licensing and feature gating, build requirements
- **[API_VERSIONING.md](API_VERSIONING.md)** - API versioning standards, deprecation process, migration guides
- **[DATABASE.md](DATABASE.md)** - Database standards, PyDAL configuration, connection management, thread safety
- **[TESTING.md](TESTING.md)** - Unit testing, integration testing, E2E testing, performance testing
- **[DOCUMENTATION.md](DOCUMENTATION.md)** - README standards, CLAUDE.md management, API documentation, architecture docs
- **[WORKFLOWS.md](WORKFLOWS.md)** - CI/CD standards, GitHub Actions, build pipelines, security scanning
- **[LICENSE_SERVER_INTEGRATION.md](licensing/license-server-integration.md)** - PenguinTech License Server integration guide

## Table of Contents

1. [Language Selection Criteria](#language-selection-criteria)
2. [ReactJS Frontend Standards](#reactjs-frontend-standards)
3. [Security Standards](#security-standards)
4. [Ansible Integration](#ansible-integration)
5. [CI/CD Standards](#cicd-standards)
6. [Web UI Design Standards](#web-ui-design-standards)
7. [Quality Checklist](#quality-checklist)

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

### Protected Routes

```javascript
// src/components/ProtectedRoute.jsx
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};
```

### React Query for Data Fetching

```javascript
// src/hooks/useUsers.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';

export const useUsers = () => {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const response = await apiClient.get('/api/users');
      return response.data;
    },
  });
};

export const useCreateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userData) => {
      const response = await apiClient.post('/api/users', userData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['users']);
    },
  });
};
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

- **ALWAYS check Dependabot alerts** before commits
- **Monitor vulnerabilities** via Socket.dev
- **Mandatory security scanning** before dependency changes
- **Fix all security alerts immediately**
- **Version pinning**: Exact versions for security-critical dependencies

### Vulnerability Response Process

1. Identify affected packages and severity
2. Update to patched versions immediately
3. Test updated dependencies thoroughly
4. Document security fixes in commit messages
5. Verify no new vulnerabilities introduced

---

## Web UI Design Standards

**ALL ReactJS frontend applications MUST follow these design patterns:**

### Core Design Principles
- **Multi-page design preferred** - avoid single-page applications for marketing sites
- **Modern aesthetic** with clean, professional appearance
- **Subtle color schemes** - not overly bright
- **Gradient usage encouraged** - subtle gradients for visual depth and modern appeal
- **Responsive design** - seamless across all device sizes
- **Performance focused** - fast loading times and optimized assets

### UI Framework Standards
- Use **Tailwind CSS** for styling
- Implement **Radix UI** or **Shadcn UI** for accessible components
- Follow **accessibility (a11y)** best practices (WCAG 2.1 AA)
- Use **Lucide React** or **Heroicons** for icons
- Implement dark mode support where applicable

### Layout Patterns
- **Elder-style collapsible sidebar** for navigation
- **Tab navigation** for feature organization
- **Gold (amber-400) text theme** for accents
- **Consistent spacing** using Tailwind spacing scale
- **Mobile-first responsive** breakpoints

For comprehensive UI guidelines, color palettes, and component examples, create detailed documentation in `docs/ui-guidelines.md`.

---

## Ansible Integration

- **Documentation Research**: ALWAYS research modules on https://docs.ansible.com
- **Module verification**: Check official docs for syntax and parameters
- **Best practices**: Follow community standards and idempotency
- **Testing**: Ensure playbooks are idempotent

---

## CI/CD Standards

For comprehensive CI/CD standards, workflow configuration, naming conventions, and security scanning requirements, see **[WORKFLOWS.md](WORKFLOWS.md)**.

**Key Principles:**
- Efficient execution with parallel builds where possible
- Mandatory security scanning for all code
- Consistent naming conventions across all projects
- Version management integration in all workflows
- Comprehensive documentation requirements
- Multi-architecture Docker builds (amd64/arm64)
- Debian-slim base images for all containers

---

## Quality Checklist

Before marking any task complete, verify:
- ✅ All error cases handled properly
- ✅ Unit tests cover all code paths
- ✅ Integration tests verify component interactions
- ✅ Security requirements fully implemented
- ✅ Performance meets acceptable standards
- ✅ Documentation complete and accurate
- ✅ Code review standards met
- ✅ No hardcoded secrets or credentials
- ✅ Logging and monitoring in place
- ✅ Build passes in containerized environment
- ✅ No security vulnerabilities in dependencies
- ✅ Edge cases and boundary conditions tested
- ✅ License enforcement configured correctly (if release-ready)
