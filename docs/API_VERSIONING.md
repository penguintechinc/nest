# API Versioning Standards

**ALL REST APIs MUST use versioning in the URL path**

## URL Structure

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

## Version Lifecycle

**Version Strategy:**
- **Current Version**: Active development and fully supported
- **Previous Version (N-1)**: Supported with bug fixes and security patches
- **Older Versions (N-2+)**: Deprecated with deprecation warning headers

**Deprecation Process:**
1. Release new major version with improvements/breaking changes
2. Support previous version for at least 12 months
3. Add deprecation header to older versions: `Deprecation: true`
4. Include sunset date header: `Sunset: 2026-01-01`
5. Return `Link` header pointing to new version documentation

**Example Deprecation Headers:**
```python
@app.route('/api/v1/users', methods=['GET'])
def get_users_v1():
    """Deprecated - use /api/v2/users instead"""
    response = make_response(jsonify(users))
    response.headers['Deprecation'] = 'true'
    response.headers['Sunset'] = 'Sun, 01 Jan 2026 00:00:00 GMT'
    response.headers['Link'] = '</api/v2/users>; rel="successor-version"'
    return response
```

## Implementation Examples

**Python (Flask):**

```python
from flask import Flask, jsonify, request, make_response
from datetime import datetime

app = Flask(__name__)

# API v1 endpoints
@app.route('/api/v1/users', methods=['GET', 'POST'])
def users_v1():
    """User management - v1"""
    if request.method == 'GET':
        users = get_all_users()
        return jsonify({'data': users, 'version': 1})
    elif request.method == 'POST':
        new_user = create_user(request.json)
        return jsonify({'data': new_user, 'version': 1}), 201

@app.route('/api/v1/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user_detail_v1(user_id):
    """Single user detail - v1"""
    if request.method == 'GET':
        user = get_user(user_id)
        return jsonify({'data': user, 'version': 1})
    elif request.method == 'PUT':
        updated_user = update_user(user_id, request.json)
        return jsonify({'data': updated_user, 'version': 1})
    elif request.method == 'DELETE':
        delete_user(user_id)
        return '', 204

# API v2 endpoints (newer version with improved structure)
@app.route('/api/v2/users', methods=['GET', 'POST'])
def users_v2():
    """User management - v2 (improved response format)"""
    if request.method == 'GET':
        users = get_all_users()
        return jsonify({
            'status': 'success',
            'data': users,
            'meta': {
                'version': 2,
                'timestamp': datetime.utcnow().isoformat(),
                'total': len(users)
            }
        })
    elif request.method == 'POST':
        new_user = create_user(request.json)
        return jsonify({
            'status': 'created',
            'data': new_user,
            'meta': {'version': 2}
        }), 201

@app.route('/api/v2/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user_detail_v2(user_id):
    """Single user detail - v2 (improved response format)"""
    if request.method == 'GET':
        user = get_user(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'error': 'User not found',
                'meta': {'version': 2}
            }), 404
        return jsonify({
            'status': 'success',
            'data': user,
            'meta': {'version': 2}
        })
    elif request.method == 'PUT':
        updated_user = update_user(user_id, request.json)
        return jsonify({
            'status': 'success',
            'data': updated_user,
            'meta': {'version': 2}
        })
    elif request.method == 'DELETE':
        delete_user(user_id)
        return jsonify({
            'status': 'success',
            'meta': {'version': 2}
        }), 204

# Deprecated v1 with warnings
@app.before_request
def add_deprecation_headers_v1():
    """Add deprecation headers for v1 endpoints"""
    if request.path.startswith('/api/v1/'):
        @app.after_request
        def add_headers(response):
            response.headers['Deprecation'] = 'true'
            response.headers['Sunset'] = 'Sun, 01 Jan 2026 00:00:00 GMT'
            response.headers['Link'] = '</api/v2' + request.path[7:] + '>; rel="successor-version"'
            response.headers['Warning'] = '299 - "v1 API is deprecated, use v2 instead"'
            return response
        return None
```

**Go:**

```go
package main

import (
    "fmt"
    "net/http"
    "time"
)

type APIResponse struct {
    Status string      `json:"status"`
    Data   interface{} `json:"data"`
    Meta   APIMeta     `json:"meta"`
}

type APIMeta struct {
    Version   int       `json:"version"`
    Timestamp time.Time `json:"timestamp,omitempty"`
}

// API v1 endpoints
func getUsersV1(w http.ResponseWriter, r *http.Request) {
    users := getAllUsers()
    response := map[string]interface{}{
        "data":    users,
        "version": 1,
    }
    writeJSON(w, http.StatusOK, response)
}

func getUserDetailV1(w http.ResponseWriter, r *http.Request) {
    // Handle GET, PUT, DELETE for /api/v1/users/{id}
}

// API v2 endpoints (improved)
func getUsersV2(w http.ResponseWriter, r *http.Request) {
    users := getAllUsers()
    response := APIResponse{
        Status: "success",
        Data:   users,
        Meta: APIMeta{
            Version:   2,
            Timestamp: time.Now().UTC(),
        },
    }
    writeJSON(w, http.StatusOK, response)
}

func getUserDetailV2(w http.ResponseWriter, r *http.Request) {
    // Handle GET, PUT, DELETE for /api/v2/users/{id}
}

// Router setup
func setupRoutes() {
    // v1 endpoints
    http.HandleFunc("/api/v1/users", getUsersV1)
    http.HandleFunc("/api/v1/users/", getUserDetailV1)

    // v2 endpoints
    http.HandleFunc("/api/v2/users", getUsersV2)
    http.HandleFunc("/api/v2/users/", getUserDetailV2)
}

// Middleware for deprecation headers
func deprecationMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if strings.HasPrefix(r.URL.Path, "/api/v1/") {
            w.Header().Set("Deprecation", "true")
            w.Header().Set("Sunset", "Sun, 01 Jan 2026 00:00:00 GMT")
            w.Header().Set("Link", fmt.Sprintf("</api/v2%s>; rel=\"successor-version\"", strings.TrimPrefix(r.URL.Path, "/api/v1")))
            w.Header().Set("Warning", "299 - \"v1 API is deprecated, use v2 instead\"")
        }
        next.ServeHTTP(w, r)
    })
}
```

## Client Migration Guide

**For Frontend Clients:**

```javascript
// src/services/apiClient.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Use v2 by default
const API_VERSION = process.env.REACT_APP_API_VERSION || 'v2';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to handle deprecation warnings
apiClient.interceptors.response.use(
  (response) => {
    // Check for deprecation header
    if (response.headers.deprecation === 'true') {
      console.warn('API endpoint is deprecated:', {
        sunset: response.headers.sunset,
        successor: response.headers.link,
      });
      // Optionally migrate to new version
    }
    return response;
  },
  (error) => Promise.reject(error)
);

// Usage
export const getUsers = () => apiClient.get('/users');
export const createUser = (userData) => apiClient.post('/users', userData);
export const updateUser = (id, userData) => apiClient.put(`/users/${id}`, userData);
export const deleteUser = (id) => apiClient.delete(`/users/${id}`);
```

**Environment Variables:**
```bash
# Default to latest stable version
REACT_APP_API_VERSION=v2

# Can override in .env files
REACT_APP_API_VERSION=v1  # For backwards compatibility during migration
```

## Backwards Compatibility

**When introducing breaking changes:**

1. **Add new version** with breaking changes
2. **Maintain previous version** for minimum 12 months
3. **Document migration path** for users
4. **Provide migration tools** or helper functions
5. **Communicate deprecation timeline** to users

**Example Migration Timeline:**
- **Month 0**: Release v2 alongside v1
- **Month 1-12**: Both versions fully supported
- **Month 12**: v1 enters sunset period
- **Month 13**: v1 endpoints return errors

## API Documentation

**ALWAYS document API versions in README and API docs:**

```markdown
## API Versions

### Current Version: v2
- Latest features and improvements
- Recommended for all new integrations
- Supported indefinitely while v2 is current

### Previous Version: v1
- Deprecated as of 2024-01-01
- Supported until 2026-01-01
- [Migration guide](docs/migration-v1-to-v2.md)

### Version Comparison

| Feature | v1 | v2 |
|---------|----|----|
| User Management | ✓ | ✓ |
| Response Format | Simple | Enhanced metadata |
| Error Handling | Basic | Detailed error codes |
| Pagination | Query params | Header-based |
```
