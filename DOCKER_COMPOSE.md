# NEST Docker Compose Configuration

This document describes the Docker Compose setup for the NEST development and production environments.

## Overview

Two comprehensive docker-compose files are provided:

- **docker-compose.yml** - Development environment with 9 services
- **docker-compose.prod.yml** - Production environment with optimizations

## Development Environment (docker-compose.yml)

### Services (9 total)

#### 1. PostgreSQL 16 Database
- **Image**: postgres:16-alpine
- **Container**: nest-postgres
- **Port**: 5432:5432
- **Default Credentials**:
  - Database: nest
  - User: nest
  - Password: nest123
- **Volume**: ./data/postgres
- **Health Check**: pg_isready
- **Features**:
  - UTF-8 encoding
  - Persistent data storage
  - Health monitoring

#### 2. Redis 7 Cache
- **Image**: redis:7-alpine
- **Container**: nest-redis
- **Port**: 6379:6379
- **Default Password**: nest123
- **Volume**: ./data/redis
- **Health Check**: redis-cli ping
- **Features**:
  - Appendonly mode enabled
  - Persistent RDB snapshots
  - Memory monitoring

#### 3. Go API Service
- **Container**: nest-api
- **Port**: 8080:8080
- **Dependencies**: postgres, redis (healthy)
- **Environment Variables**:
  - DB_HOST=postgres
  - DB_PORT=5432
  - DB_NAME=nest
  - REDIS_HOST=redis
  - JWT_SECRET=dev-secret-key-change-in-prod
  - GIN_MODE=debug
  - LOG_LEVEL=debug
- **Volumes**: ./apps/api:/app (hot reload)
- **Health Check**: /healthz endpoint
- **Features**:
  - Live reload via air
  - Debug logging enabled
  - Development-optimized

#### 4. Python Manager Service
- **Container**: nest-manager
- **Port**: 8000:8000
- **Dependencies**: postgres, redis (healthy)
- **Environment Variables**:
  - DB_HOST=postgres
  - DB_PORT=5432
  - DB_NAME=nest
  - REDIS_HOST=redis
  - PORT=8000
  - DEBUG=true
  - LOG_LEVEL=DEBUG
  - PYTHONUNBUFFERED=1
- **Volumes**: ./apps/manager:/app (live reload)
- **Health Check**: /healthz endpoint
- **Features**:
  - Quart async framework
  - Live code reload
  - Full debug logging

#### 5. React Frontend with Vite
- **Container**: nest-web
- **Port**: 3000:3000
- **Dependencies**: api, manager
- **Environment Variables**:
  - NODE_ENV=development
  - VITE_API_URL=http://localhost:8080
  - VITE_MANAGER_URL=http://localhost:8000
- **Volumes**: ./web:/app (live reload)
- **Health Check**: HTTP 200 status
- **Features**:
  - Hot module replacement (HMR)
  - Development server
  - TypeScript support

#### 6. Database Initialization
- **Container**: nest-db-init
- **Purpose**: One-time database schema initialization
- **Command**: python db_init.py
- **Restart Policy**: no (runs once)
- **Dependencies**: postgres, redis (healthy)
- **Features**:
  - Automatic schema creation
  - Initial data seeding
  - Migration support

#### 7. Prometheus Monitoring
- **Image**: prom/prometheus:latest
- **Container**: nest-prometheus
- **Port**: 9090:9090
- **Volume**: ./infrastructure/monitoring/prometheus
- **Data Volume**: ./data/prometheus
- **Configuration**: prometheus.yml
- **Features**:
  - Time-series metrics storage
  - 200 hours retention
  - Lifecycle management enabled

#### 8. Grafana Dashboards
- **Image**: grafana/grafana:latest
- **Container**: nest-grafana
- **Port**: 3001:3000
- **Default Credentials**: admin / admin123
- **Volumes**:
  - ./infrastructure/monitoring/grafana/provisioning
  - ./infrastructure/monitoring/grafana/dashboards
- **Data Volume**: ./data/grafana
- **Features**:
  - Dashboard visualization
  - Prometheus integration
  - Pre-configured dashboards

#### 9. Nginx Reverse Proxy
- **Image**: nginx:alpine
- **Container**: nest-nginx
- **Ports**: 80:80, 443:443
- **Configuration**: ./infrastructure/docker/nginx/
- **Log Volume**: ./data/logs/nginx
- **Features**:
  - SSL/TLS support
  - Load balancing
  - Request routing
  - Gzip compression

### Network Configuration

- **Network Name**: nest-network
- **Driver**: bridge
- **MTU**: 1500

### Volume Configuration

All volumes use local bind mounts for easy access:
- `./data/postgres` - Database files
- `./data/redis` - Cache files
- `./data/prometheus` - Metrics data
- `./data/grafana` - Dashboard data
- `./data/logs/nginx` - Web server logs

### Quick Start

```bash
# Start all development services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop services
docker-compose down

# Reset database and cache
docker-compose down -v
rm -rf data/
```

### Service Dependencies

```
postgres (health check)
    ↓
redis (health check)
    ↓
├── api
├── manager
└── db-init

web
    ├── depends on: api
    └── depends on: manager

prometheus
    ├── depends on: api
    └── depends on: manager

grafana
    └── depends on: prometheus

nginx
    ├── depends on: api
    ├── depends on: manager
    └── depends on: web
```

## Production Environment (docker-compose.prod.yml)

### Key Differences from Development

#### 1. No Volume Mounts
- Immutable containers
- Images are pre-built
- No hot reload capability

#### 2. Container Images
- Uses pre-built images from registry: `${DOCKER_REGISTRY}/nest-{service}:${IMAGE_TAG}`
- Requires images to be built and pushed before deployment

#### 3. Resource Limits
Each service has defined CPU and memory limits:

| Service | CPU Limit | Memory Limit | CPU Reserve | Memory Reserve |
|---------|-----------|--------------|-------------|----------------|
| postgres | 2 cores | 2GB | 1 core | 1GB |
| redis | 1 core | 1GB | 0.5 core | 512MB |
| api | 1 core | 512MB | 0.5 core | 256MB |
| manager | 1 core | 512MB | 0.5 core | 256MB |
| web | 0.5 core | 256MB | 0.25 core | 128MB |
| nginx | 0.5 core | 256MB | 0.25 core | 128MB |
| prometheus | 1 core | 512MB | 0.5 core | 256MB |
| grafana | 0.5 core | 256MB | 0.25 core | 128MB |

#### 4. Replication
Production services are replicated for high availability:
- API: 2 replicas
- Manager: 2 replicas
- Web: 2 replicas
- Nginx: 2 replicas

#### 5. Update Strategy
Rolling updates with:
- 1 container updated at a time
- 10-second delay between updates
- Automatic rollback on failure

#### 6. Logging Configuration
- JSON logging driver
- Log rotation: 10MB per file, 3-5 files max
- Service labels attached to all logs

#### 7. TLS/SSL Configuration
- Nginx enforces HTTPS
- Redis with TLS enabled
- Database with SSL mode "require"
- External URLs configured via environment variables

#### 8. Production Environment Variables
Required environment variables for production:

```bash
# Registry and Image Configuration
DOCKER_REGISTRY=registry.example.com/nest
IMAGE_TAG=v1.0.0

# Database (Required)
POSTGRES_DB=nest_production
POSTGRES_USER=nest_user
POSTGRES_PASSWORD=<secure-password>
POSTGRES_PORT=5432

# Redis (Required)
REDIS_PASSWORD=<secure-password>
REDIS_MAX_MEMORY=1gb

# API Configuration
JWT_SECRET=<secure-random-key>
LICENSE_KEY=PENG-XXXX-XXXX-XXXX-XXXX-ABCD
PRODUCT_NAME=nest

# Grafana (Required)
GRAFANA_USER=admin
GRAFANA_PASSWORD=<secure-password>
GRAFANA_ROOT_URL=https://grafana.example.com

# Frontend URLs
VITE_API_URL=https://api.example.com
VITE_MANAGER_URL=https://manager.example.com

# Prometheus External URL
PROMETHEUS_EXTERNAL_URL=https://prometheus.example.com

# Nginx Ports
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
```

### Production Deployment

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale api=3 --scale manager=3

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Stop all services
docker-compose -f docker-compose.prod.yml down
```

## Environment Variables

### Common Variables (.env file)

```bash
# Database
POSTGRES_DB=nest
POSTGRES_USER=nest
POSTGRES_PASSWORD=nest123
POSTGRES_PORT=5432

# Redis
REDIS_PASSWORD=nest123
REDIS_PORT=6379

# Ports
API_PORT=8080
MANAGER_PORT=8000
WEB_PORT=3000
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# Security
JWT_SECRET=dev-secret-key-change-in-prod

# License
LICENSE_KEY=PENG-XXXX-XXXX-XXXX-XXXX-ABCD
PRODUCT_NAME=nest
LICENSE_SERVER_URL=https://license.penguintech.io

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123

# Application
NODE_ENV=development
GIN_MODE=debug
LOG_LEVEL=debug
```

## Health Checks

All services include health checks with configuration:

```yaml
healthcheck:
  test: [CMD, curl, -f, http://localhost:PORT/healthz]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s-30s
```

To check service health:

```bash
# View health status
docker-compose ps

# Check specific service
docker inspect nest-api | grep -A 5 "Health"
```

## Networking

Services communicate via service name (DNS resolution):

```
# From API service
postgres:5432
redis:6379

# From Manager service
postgres:5432
redis:6379

# From Frontend
api:8080
manager:8000
```

Direct host access (for local development):
- API: http://localhost:8080
- Manager: http://localhost:8000
- Web: http://localhost:3000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

## Data Persistence

### Development
Data persists in `./data/` directory structure:
- `./data/postgres/` - PostgreSQL database files
- `./data/redis/` - Redis RDB snapshots
- `./data/prometheus/` - Metrics time-series database
- `./data/grafana/` - Grafana configuration and dashboards
- `./data/logs/nginx/` - Nginx access and error logs

### Production
Uses Docker named volumes managed by Docker:
- Docker handles volume lifecycle
- Can be backed by:
  - Local storage
  - Network-attached storage (NAS)
  - Cloud storage (EBS, GCS, etc.)

## Common Tasks

### Restart a Service
```bash
docker-compose restart api
```

### Rebuild a Service
```bash
docker-compose up -d --build api
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 50 lines
docker-compose logs --tail=50 api

# JSON format with timestamps
docker-compose logs --timestamps api
```

### Access Service Shell
```bash
# API container
docker exec -it nest-api /bin/sh

# Manager container
docker exec -it nest-manager /bin/bash

# Database
docker exec -it nest-postgres psql -U nest -d nest
```

### Monitor Resources
```bash
# Real-time resource usage
docker stats

# Specific services
docker stats nest-api nest-manager
```

## Troubleshooting

### Database Connection Issues
```bash
# Check database health
docker-compose exec postgres pg_isready -U nest

# View database logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U nest -d nest
```

### Redis Connection Issues
```bash
# Check Redis health
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis

# Check Redis memory
docker-compose exec redis redis-cli info memory
```

### API Service Not Starting
```bash
# Check API logs
docker-compose logs api

# Check if port is already in use
lsof -i :8080

# Rebuild and restart
docker-compose up -d --build api
```

### Manager Service Issues
```bash
# Check Manager logs
docker-compose logs manager

# Check Python version
docker-compose exec manager python --version

# Check installed packages
docker-compose exec manager pip list
```

### Frontend Not Loading
```bash
# Check build logs
docker-compose logs web

# Check Node version
docker-compose exec web node --version

# Clear node_modules and reinstall
docker-compose exec web rm -rf node_modules package-lock.json
docker-compose up -d --build web
```

## Performance Optimization

### Development
1. Enable volume caching for faster file operations
2. Use named volumes for dependencies (node_modules, .venv)
3. Implement hot reload for rapid development

### Production
1. Pre-build images with all dependencies
2. Use container resource limits
3. Implement health checks and auto-restart
4. Enable horizontal scaling for stateless services
5. Use external storage for persistent data
6. Implement load balancing with Nginx

## Security Considerations

### Development
- Default credentials are weak (for development only)
- TLS not enforced
- Debug logging enabled
- CORS permissive

### Production
- Strong passwords required (environment variables)
- TLS/HTTPS enforced
- Production logging (no debug)
- CORS restricted to known origins
- Database SSL required
- Redis password protected
- Resource limits enforced
- Non-root container users
- Read-only filesystems where possible

## Scaling

### Horizontal Scaling (Production)

```bash
# Scale API to 3 replicas
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Scale Manager to 3 replicas
docker-compose -f docker-compose.prod.yml up -d --scale manager=3

# Scale Web to 2 replicas
docker-compose -f docker-compose.prod.yml up -d --scale web=2
```

### Vertical Scaling

Adjust resource limits in docker-compose.prod.yml:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1G
    reservations:
      cpus: '1'
      memory: 512M
```

## Monitoring and Metrics

Access monitoring dashboards:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001

Metrics are exposed by:
- API service: http://localhost:8080/metrics
- Manager service: http://localhost:8000/metrics

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Redis Docker Image](https://hub.docker.com/_/redis)
- [Nginx Docker Image](https://hub.docker.com/_/nginx)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

## Support

For issues with the Docker Compose setup:
1. Check the logs: `docker-compose logs`
2. Verify service health: `docker-compose ps`
3. Review environment variables in `.env` file
4. Check port availability: `netstat -tuln | grep LISTEN`
5. Consult the troubleshooting section above
