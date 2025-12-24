# NEST Docker Compose Quick Start Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM for containers
- 10GB free disk space

## Installation

### macOS (with Docker Desktop)
Docker Desktop includes both Docker and Docker Compose:
```bash
# Install Docker Desktop
brew install --cask docker

# Verify installation
docker --version
docker-compose --version
```

### Linux (Ubuntu/Debian)
```bash
# Install Docker
sudo apt-get update
sudo apt-get install -y docker.io docker-compose

# Add current user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

### Windows (with WSL2)
1. Install Docker Desktop for Windows
2. Enable WSL2 backend in Docker Desktop settings
3. Use WSL2 terminal for all commands

## Quick Start (5 minutes)

### 1. Clone and Setup
```bash
cd /home/penguin/code/Nest

# Create environment file (copy from template)
cp .env.example .env

# Create data directories
mkdir -p data/{postgres,redis,prometheus,grafana,logs/nginx}
```

### 2. Start Development Environment
```bash
# Start all services (background)
docker-compose up -d

# Or with logs visible
docker-compose up

# Wait for all services to be healthy (~30s)
docker-compose ps
```

### 3. Verify Services Are Running
```bash
# Check status of all services
docker-compose ps

# Should see all services with status "Up" (not "Exit" or "Restarting")
```

### 4. Access Applications
Once all services are healthy:

- **API**: http://localhost:8080
- **Manager**: http://localhost:8000
- **Web Frontend**: http://localhost:3000
- **Grafana Dashboard**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Nginx**: http://localhost (proxy)

### 5. Initialize Database
```bash
# Manually run db initialization (if needed)
docker-compose exec db-init python db_init.py

# Or check logs to see if it auto-ran
docker-compose logs db-init
```

## Common Commands

### Start Services
```bash
# Start all services in background
docker-compose up -d

# Start with full output/logs
docker-compose up

# Start specific service
docker-compose up -d api
```

### Stop Services
```bash
# Stop all services (keep volumes)
docker-compose down

# Stop and remove all data
docker-compose down -v

# Stop without removing containers
docker-compose stop

# Stop specific service
docker-compose stop api
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f manager
docker-compose logs -f web

# Last 50 lines
docker-compose logs --tail=50 api

# With timestamps
docker-compose logs --timestamps api
```

### Rebuild Services
```bash
# Rebuild all images
docker-compose build

# Rebuild specific service
docker-compose build api

# Rebuild and restart
docker-compose up -d --build api
```

### Check Service Health
```bash
# Check all services
docker-compose ps

# Check specific service logs for health
docker-compose logs api | grep -i health

# Manual health check (API example)
curl http://localhost:8080/healthz
curl http://localhost:8000/healthz
```

### Database Commands
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U nest -d nest

# Check if database is ready
docker-compose exec postgres pg_isready -U nest

# View database logs
docker-compose logs postgres
```

### Redis Commands
```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli -a nest123

# Check Redis status
docker-compose exec redis redis-cli info

# Ping Redis
docker-compose exec redis redis-cli ping
```

### Container Shell Access
```bash
# API container (Go)
docker exec -it nest-api /bin/sh

# Manager container (Python)
docker exec -it nest-manager /bin/bash

# Web container (Node.js)
docker exec -it nest-web /bin/bash

# Database
docker exec -it nest-postgres /bin/bash
```

## Troubleshooting

### Services Won't Start

**Problem**: Services show "Exit" or "Restarting" status

```bash
# Check service logs
docker-compose logs api
docker-compose logs manager

# Common issues:
# - Port already in use
# - Database not ready
# - Configuration error
```

**Solution**:
```bash
# Check which processes are using ports
lsof -i :8080  # API port
lsof -i :8000  # Manager port
lsof -i :3000  # Web port
lsof -i :5432  # Database port

# Kill process using port (if needed)
kill -9 <PID>

# Or change ports in .env file
# Then restart services
docker-compose restart
```

### Database Connection Issues

**Problem**: Services can't connect to PostgreSQL

```bash
# Check database is running and healthy
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Connect directly to verify
docker-compose exec postgres psql -U nest -d nest -c "SELECT 1"
```

**Solution**:
```bash
# Restart database
docker-compose restart postgres

# Wait a few seconds for startup
sleep 5

# Restart dependent services
docker-compose restart api manager
```

### Redis Connection Issues

**Problem**: Redis connection failures

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

**Solution**:
```bash
# Restart Redis
docker-compose restart redis

# Or reset Redis data
docker-compose down -v
docker-compose up -d redis
```

### Out of Disk Space

**Problem**: Docker containers taking too much space

```bash
# Check Docker disk usage
docker system df

# Clean up unused images, containers, and volumes
docker system prune -a

# Or more aggressive cleanup
docker system prune -a --volumes
```

### Port Conflicts

**Problem**: Port already in use error

Edit `.env` file and change ports:
```bash
API_PORT=8081          # Was 8080
MANAGER_PORT=8001      # Was 8000
WEB_PORT=3001          # Was 3000
POSTGRES_PORT=5433     # Was 5432
REDIS_PORT=6380        # Was 6379
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Development Workflow

### Making Code Changes

The development environment supports **hot reload** for:
- **API**: Changes to Go code auto-reload (air)
- **Manager**: Python code auto-reloads (file watching)
- **Web**: JavaScript/TypeScript changes auto-reload (Vite HMR)

Just edit files and save - no restart needed!

### Running Tests

```bash
# API tests
docker-compose exec api go test ./...

# Manager tests
docker-compose exec manager pytest tests/

# Web tests
docker-compose exec web npm test
```

### Running Commands in Containers

```bash
# Run Go command
docker-compose exec api go mod download

# Run Python command
docker-compose exec manager pip install -r requirements.txt

# Run NPM command
docker-compose exec web npm install
```

## Production Deployment

For production deployment, use `docker-compose.prod.yml`:

```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Set required environment variables first (.env)
# DOCKER_REGISTRY=my-registry.com/nest
# IMAGE_TAG=v1.0.0
# POSTGRES_PASSWORD=<strong-password>
# etc.

# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Stop production environment
docker-compose -f docker-compose.prod.yml down
```

## Useful Docker Commands

```bash
# View all containers
docker ps -a

# View Docker system info
docker system info

# View resource usage
docker stats

# View specific container stats
docker stats nest-api

# Prune unused resources
docker image prune
docker container prune
docker volume prune
docker network prune

# View docker logs (daemon logs)
docker logs <container-name>

# Copy file from container
docker cp nest-api:/app/file.txt ./

# Copy file to container
docker cp ./file.txt nest-api:/app/
```

## Environment Variables

### Modify .env File

```bash
# Database configuration
POSTGRES_DB=nest
POSTGRES_USER=nest
POSTGRES_PASSWORD=nest123

# Redis configuration
REDIS_PASSWORD=nest123

# Port configuration
API_PORT=8080
MANAGER_PORT=8000
WEB_PORT=3000

# License configuration
LICENSE_KEY=PENG-XXXX-XXXX-XXXX-XXXX-ABCD
PRODUCT_NAME=nest
```

Then restart services to apply changes:
```bash
docker-compose down
docker-compose up -d
```

## Monitoring

### Grafana Dashboards

1. Open http://localhost:3001
2. Login with admin/admin123
3. View pre-configured dashboards
4. Add custom dashboards as needed

### Prometheus Metrics

1. Open http://localhost:9090
2. Query metrics (example queries):
   - `up` - Service status
   - `http_request_duration_seconds` - Request duration
   - `postgres_up` - Database status
   - `redis_up` - Redis status

### View Service Metrics

```bash
# API metrics endpoint
curl http://localhost:8080/metrics

# Manager metrics endpoint
curl http://localhost:8000/metrics
```

## Performance Tips

### Development
1. Use SSD for data directory (faster database I/O)
2. Allocate sufficient RAM to Docker (at least 4GB)
3. Monitor Docker resource usage: `docker stats`
4. Use named volumes for dependencies

### Production
1. Use container resource limits (configured)
2. Enable horizontal scaling
3. Use external storage for data
4. Configure backups for database
5. Monitor with Prometheus/Grafana

## Next Steps

1. Read full documentation: `DOCKER_COMPOSE.md`
2. Configure `.env` file for your environment
3. Set up IDE debuggers for containers
4. Configure CI/CD pipeline
5. Set up backups for data volumes

## Help & Support

### Check Logs First
```bash
docker-compose logs -f <service-name>
```

### Common Log Locations
- API: logs to stdout
- Manager: logs to stdout
- Web: logs to stdout/browser console
- Database: `docker-compose logs postgres`

### Documentation
- Full guide: `/home/penguin/code/Nest/DOCKER_COMPOSE.md`
- Docker reference: https://docs.docker.com/compose/
- Service-specific docs in `docs/` folder
