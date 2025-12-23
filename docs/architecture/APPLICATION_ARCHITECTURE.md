# Application Architecture Requirements

## Overview

This document outlines the standard application architecture patterns and requirements for all Penguin Tech Inc projects. These guidelines ensure consistency, maintainability, and enterprise-grade quality across all applications built using the project template.

All applications must follow these architectural standards to ensure proper integration with the broader enterprise infrastructure, licensing systems, and operational requirements.

---

## Web Framework Standards

### py4web as Primary Framework

- **Primary Framework**: Use py4web for ALL application web structures (sales/docs websites exempt)
- **Why py4web**: Provides rapid development, built-in security features, and excellent integration with PyDAL
- **Application Scope**: Web applications, REST APIs, and internal services

### Required Health Endpoints

ALL applications must implement a health check endpoint:

```python
from py4web import action

@action('healthz')
def health_check():
    """Health check endpoint for load balancers and monitoring systems"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': os.getenv('APP_VERSION', 'unknown')
    }
```

### Metrics Endpoints

ALL applications must expose Prometheus-compatible metrics:

```python
from py4web import action
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

@action('metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), {'Content-Type': 'text/plain; charset=utf-8'}

# Use in request handlers
@action('api/users', method=['GET'])
def api_users():
    start_time = time.time()
    try:
        users = db(db.users).select().as_list()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/users', status='200').inc()
        return {'users': users}
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/api/users', status='500').inc()
        raise
    finally:
        REQUEST_DURATION.labels(method='GET', endpoint='/api/users').observe(
            time.time() - start_time
        )
```

---

## Logging & Monitoring

### Console Logging

Always implement console output for application logs:

```python
import logging
import sys
from datetime import datetime

class StructuredLogger:
    def __init__(self, name, verbosity=2):
        self.logger = logging.getLogger(name)
        self.verbosity = verbosity  # 1=warnings, 2=info, 3=debug

        # Configure handler
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Set level based on verbosity
        level_map = {1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}
        self.logger.setLevel(level_map.get(verbosity, logging.INFO))

    def info(self, msg):
        self.logger.info(msg)

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def error(self, msg):
        self.logger.error(msg)

# Usage
logger = StructuredLogger(__name__, verbosity=2)
logger.info("Application started")
```

### Multi-Destination Logging

Support multiple log destinations for different deployment scenarios:

#### UDP Syslog (Legacy)

```python
import logging.handlers

# Legacy syslog support
syslog_handler = logging.handlers.SysLogHandler(
    address=('localhost', 514),
    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
)
logger.addHandler(syslog_handler)
```

#### HTTP3/QUIC to Kafka (Modern)

```python
import asyncio
import json
from datetime import datetime

class KafkaHTTP3Logger:
    """Log to Kafka cluster via HTTP3/QUIC protocol"""

    def __init__(self, kafka_broker_url, topic='app-logs'):
        self.kafka_broker_url = kafka_broker_url
        self.topic = topic

    async def send_log(self, level, message, metadata=None):
        """Send structured log to Kafka via HTTP3"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'message': message,
            'metadata': metadata or {},
            'correlation_id': self._get_correlation_id()
        }

        # Use HTTP3/QUIC for high-performance logging
        # (implementation requires h3 library or similar)
        await self._send_via_http3(json.dumps(log_entry))

    def _get_correlation_id(self):
        """Get or generate correlation ID for request tracing"""
        # Implementation depends on request context
        pass

    async def _send_via_http3(self, data):
        """Send data via HTTP3/QUIC"""
        # Implementation using h3 or equivalent HTTP3 client
        pass
```

#### Cloud-Native Logging (AWS/GCP)

```python
import logging
from watchtower import CloudWatchLogHandler  # AWS CloudWatch
# or google.cloud.logging for GCP

# AWS CloudWatch
cloudwatch_handler = CloudWatchLogHandler(
    log_group='app-logs',
    stream_name='production'
)
logger.addHandler(cloudwatch_handler)

# GCP Cloud Logging
from google.cloud import logging as gcp_logging
gcp_client = gcp_logging.Client()
gcp_handler = gcp_client.logging_handler_class()
logger.addHandler(gcp_handler)
```

### Logging Levels with getopts

Implement standardized verbosity levels using Python's getopts:

```python
import getopt
import sys

def parse_arguments():
    """Parse command line arguments"""
    verbosity = 2  # Default to info level

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'v')
    except getopt.GetoptError as e:
        print(f"Error: {e}")
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-v':
            verbosity += 1

    return verbosity

def get_log_level(verbosity):
    """Map verbosity count to log level"""
    levels = {
        1: 'WARNING',      # -v: Warnings and criticals only
        2: 'INFO',         # -vv: Info level (default)
        3: 'DEBUG'         # -vvv: Debug logging
    }
    return levels.get(min(verbosity, 3), 'INFO')

# Usage
if __name__ == '__main__':
    verbosity = parse_arguments()
    log_level = get_log_level(verbosity)
    logger = StructuredLogger(__name__, verbosity=verbosity)
    logger.info(f"Logging level: {log_level}")
```

---

## Database & Caching Standards

### PostgreSQL as Default Database

All applications default to PostgreSQL with proper security and isolation:

```python
from pydal import DAL, Field

# Connect with non-root user to dedicated database
db = DAL(
    'postgresql://app_user:secure_password@db_host:5432/app_db',
    migrate=True,
    fake_migrate=False,
    pool_size=10,
    check_reserved=['all']
)

# Define tables with proper validation
db.define_table('users',
    Field('username', 'string', requires=[IS_NOT_EMPTY(), IS_ALPHANUMERIC()]),
    Field('email', 'string', requires=IS_EMAIL()),
    Field('created_at', 'datetime', default=datetime.datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table('sessions',
    Field('user_id', 'reference users'),
    Field('token', 'string', requires=IS_NOT_EMPTY()),
    Field('expires_at', 'datetime'),
    migrate=True
)

# Commit tables to database
db.commit()
```

### PyDAL Usage Guidelines

Only use PyDAL for databases with full PyDAL support:

```python
# Supported databases with full PyDAL support
# - PostgreSQL
# - MySQL
# - SQLite (development only)
# - Oracle (limited support)

# DO NOT use PyDAL for:
# - MongoDB (use motor/pymongo directly)
# - DynamoDB (use boto3 directly)
# - Any NoSQL database without PyDAL adapters
```

### Redis/Valkey Caching

Utilize Redis/Valkey for high-performance caching with optional security:

```python
import redis
import json
from typing import Any, Optional

class CacheManager:
    def __init__(self, host='localhost', port=6379, use_tls=True, password=None):
        """Initialize Redis/Valkey connection"""
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            ssl=use_tls,
            ssl_cert_reqs='required',
            decode_responses=True
        )

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set cache value with TTL"""
        self.redis_client.setex(
            key,
            ttl,
            json.dumps(value)
        )

    def get(self, key: str) -> Optional[Any]:
        """Get cache value"""
        value = self.redis_client.get(key)
        return json.loads(value) if value else None

    def delete(self, key: str):
        """Delete cache entry"""
        self.redis_client.delete(key)

    def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)

# Usage
cache = CacheManager(host='redis', password=os.getenv('REDIS_PASSWORD'))
cache.set('user:123', {'id': 123, 'name': 'John'}, ttl=3600)
user_data = cache.get('user:123')
```

---

## Security Implementation

### TLS Enforcement

Enforce minimum TLS 1.2 with preference for TLS 1.3:

```python
import ssl
from py4web import action

# Configure TLS settings
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(
    certfile='/path/to/cert.pem',
    keyfile='/path/to/key.pem'
)

# Enforce TLS 1.2 minimum, prefer TLS 1.3
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1

# Set strong cipher suites
ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:!aNULL:!eNULL:!EXPORT:!DSS:!DES:!RC4:!3DES:!MD5:!PSK')
```

### HTTPS Connection Standards

Use HTTPS for all connections where possible:

```python
import requests

# Enforce HTTPS with certificate verification
session = requests.Session()
session.verify = True  # Verify SSL certificates

# Disable insecure connection methods
response = session.get(
    'https://api.example.com/endpoint',
    verify=True,  # Require SSL verification
    timeout=30
)
```

### WireGuard for Alternative Connections

Use WireGuard where HTTPS is not available:

```bash
# WireGuard configuration example
[Interface]
PrivateKey = <private_key>
Address = 10.0.0.1/24

[Peer]
PublicKey = <peer_public_key>
Endpoint = example.com:51820
AllowedIPs = 10.0.0.0/24
```

### Modern Logging Transport

Use HTTP3/QUIC for Kafka and cloud logging services:

```python
# HTTP3/QUIC configuration for logging services
# Example implementation would use h3 or similar
LOG_TRANSPORT = {
    'protocol': 'HTTP3',
    'compression': 'gzip',
    'batch_size': 1000,
    'flush_interval': 60
}
```

### Standard Security Implementation

Implement JWT, MFA, and mTLS:

```python
from datetime import datetime, timedelta
import jwt
import os

class JWTManager:
    """JWT token management with standard claims"""

    def __init__(self, secret_key=None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET')
        self.algorithm = 'HS256'

    def generate_token(self, user_id, expiration_hours=24):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expiration_hours)
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token):
        """Verify and decode JWT token"""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError:
            raise Exception("Invalid token")

# MFA Implementation
class MFAManager:
    """Multi-factor authentication manager"""

    def __init__(self):
        import pyotp
        self.totp = pyotp

    def generate_secret(self):
        """Generate MFA secret for user"""
        return self.totp.random_base32()

    def verify_code(self, secret, code):
        """Verify TOTP code"""
        totp = self.totp.TOTP(secret)
        return totp.verify(code)

# mTLS Configuration
mTLS_CONFIG = {
    'client_cert': '/path/to/client.crt',
    'client_key': '/path/to/client.key',
    'ca_cert': '/path/to/ca.crt',
    'verify': True
}
```

### Enterprise SSO

SAML/OAuth2 SSO as enterprise-only features:

```python
from saml2 import METADATA_SCHEMA, SAMLClient
from authlib.integrations.requests_client import OAuth2Session

# SAML Configuration (Enterprise)
SAML_CONFIG = {
    'entityID': 'your-app-entity-id',
    'metadata': {
        'local': ['metadata.xml']
    },
    'service': {
        'sp': {
            'endpoints': {
                'assertion_consumer_service': [
                    ('https://app.example.com/acs', 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST')
                ]
            }
        }
    }
}

# OAuth2 Configuration (Enterprise)
OAUTH2_CONFIG = {
    'client_id': os.getenv('OAUTH_CLIENT_ID'),
    'client_secret': os.getenv('OAUTH_CLIENT_SECRET'),
    'authorize_url': 'https://sso.example.com/oauth2/authorize',
    'token_url': 'https://sso.example.com/oauth2/token',
    'userinfo_url': 'https://sso.example.com/oauth2/userinfo'
}
```

---

## Ansible Integration Requirements

### Documentation Research

ALWAYS research Ansible modules on https://docs.ansible.com before implementation.

### Module Verification Checklist

Before implementing any Ansible module, verify:

- [ ] Correct module names and syntax from official documentation
- [ ] Required and optional parameters are correctly specified
- [ ] Return values and data structures are properly handled
- [ ] Version compatibility and requirements
- [ ] Idempotency considerations

### Best Practices

Follow Ansible community standards and idempotency principles:

```yaml
---
- name: Deploy Application
  hosts: app_servers
  vars:
    app_version: "{{ lookup('env', 'APP_VERSION') }}"
    app_user: app_user

  tasks:
    # Idempotent task: Create user only if not exists
    - name: Create application user
      user:
        name: "{{ app_user }}"
        shell: /bin/bash
        createhome: yes
        state: present

    # Idempotent task: Install packages
    - name: Install dependencies
      apt:
        name: "{{ item }}"
        state: present
      loop:
        - python3
        - python3-pip
        - postgresql-client

    # Idempotent task: Deploy application
    - name: Deploy application
      git:
        repo: "{{ git_repo }}"
        dest: "/opt/app"
        version: "{{ app_version }}"
        force: yes
      notify: restart application

    # Proper error handling
    - name: Run database migrations
      shell: |
        cd /opt/app
        python manage.py migrate
      register: migration_result
      failed_when:
        - migration_result.rc != 0
        - "'no migration to apply' not in migration_result.stdout"

  handlers:
    - name: restart application
      systemd:
        name: app
        state: restarted
        daemon_reload: yes
```

### Testing Playbooks for Idempotency

```yaml
---
- name: Test playbook idempotency
  hosts: localhost
  tasks:
    - name: Run playbook first time
      shell: ansible-playbook deploy.yml
      register: first_run

    - name: Run playbook second time
      shell: ansible-playbook deploy.yml
      register: second_run

    - name: Verify idempotency
      assert:
        that:
          - second_run.rc == 0
          - "'changed=0' in second_run.stdout"
        fail_msg: "Playbook is not idempotent"
```

---

## Website Integration Requirements

### Dual Website Structure

Each project MUST have two dedicated websites:

1. **Marketing/Sales Website**: Node.js based
2. **Documentation Website**: Markdown based

### Website Design Preferences

Guidelines for website aesthetics and functionality:

- **Multi-page Design**: Preferred over single-page applications for marketing sites
- **Modern Aesthetic**: Clean, professional appearance
- **Color Scheme**: Not overly bright - use subtle, sophisticated color schemes
- **Gradients**: Subtle gradients for visual depth and modern appeal
- **Responsive Design**: Must work seamlessly across all device sizes
- **Performance**: Fast loading times and optimized assets

### Website Repository Integration

Integrate both websites using a sparse checkout submodule:

```bash
# First, verify folder structure exists in website repo
git clone https://github.com/penguintechinc/website.git temp-website
cd temp-website

# Create project folders if they don't exist
mkdir -p {app_name}/
mkdir -p {app_name}-docs/

# Initialize Node.js marketing website (if empty)
if [ ! -f {app_name}/package.json ]; then
    echo "Creating initial marketing website structure..."
    # Add basic package.json, index.js, etc.
fi

# Initialize documentation website (if empty)
if [ ! -f {app_name}-docs/README.md ]; then
    echo "Creating initial docs website structure..."
    # Add basic markdown structure
fi

# Commit and push changes
git add .
git commit -m "Initialize website folders for {app_name}"
git push origin main
cd .. && rm -rf temp-website
```

### Sparse Submodule Setup

Add the website repository as a sparse submodule with only project-specific folders:

```bash
# Add sparse submodule
git submodule add --name websites https://github.com/penguintechinc/website.git websites
git config -f .gitmodules submodule.websites.sparse-checkout true

# Configure sparse checkout to only include project folders
echo "{app_name}/" > .git/modules/websites/info/sparse-checkout
echo "{app_name}-docs/" >> .git/modules/websites/info/sparse-checkout

# Initialize sparse checkout
git submodule update --init websites

# Add to git
git add .gitmodules .git/modules/websites/info/sparse-checkout
git commit -m "Add website submodule with sparse checkout"
```

### Website Maintenance

Both websites must be kept current with project releases and feature updates:

- Update marketing website with new features and releases
- Maintain documentation website synchronized with API changes
- Keep deployment information current
- Update feature descriptions and capabilities
- Maintain compatibility information

### First-Time Setup

If project folders don't exist in the website repository before setting up the submodule:

1. Clone the website repository
2. Create project-specific folders (`{app_name}/` and `{app_name}-docs/`)
3. Initialize with basic templates
4. Commit and push to remote
5. Then proceed with sparse submodule setup

This ensures the submodule points to valid folders containing content.

---

## Summary

Following these application architecture requirements ensures:

- **Consistency**: Standardized patterns across all projects
- **Enterprise-Grade Quality**: Security, monitoring, and reliability
- **Operational Excellence**: Proper logging, metrics, and health checks
- **Scalability**: Efficient caching and database strategies
- **Security**: TLS, authentication, and secure communication
- **Documentation**: Well-maintained marketing and technical documentation

All new applications should adhere to these standards from inception to ensure seamless integration with Penguin Tech infrastructure and best practices.
