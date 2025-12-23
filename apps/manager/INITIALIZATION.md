# Database Initialization Guide

## Overview

The Flask-Security-Too + SQLAlchemy initialization script (`db_init.py`) is a one-time setup utility that creates and seeds the Manager application database.

## Files Created

### 1. **db_init.py** (348 lines)
- Main initialization script using Flask-Security-Too and SQLAlchemy
- Creates all required database tables
- Initializes default "Global" team
- Seeds resource type catalog (14 types across 3 categories)
- Includes comprehensive error handling and logging
- Idempotent design (safe to run multiple times)

**Key Classes:**
- `DatabaseConfig`: Environment variable configuration management
- `Role`: User role model (Flask-Security-Too)
- `User`: User account model (Flask-Security-Too)
- `RolesUsers`: User-role association table
- `Team`: Team/organization model
- `ResourceType`: Supported resource types catalog

**Key Functions:**
- `main()`: Orchestrates entire initialization process
- `create_tables()`: Creates all SQLAlchemy models in PostgreSQL
- `create_default_team()`: Creates the Global team
- `seed_resource_types()`: Populates 14 resource types
- `verify_database()`: Validates setup completion
- `print_success_summary()`: Displays initialization results

### 2. **__init__.py** (9 lines)
- Package initialization file
- Documents purpose of manager application
- Sets version information

### 3. **requirements.txt** (15 lines)
- Python dependency specifications
- Flask and Flask-Security-Too packages
- SQLAlchemy ORM framework
- PostgreSQL psycopg2 driver
- Supporting utilities (email validation, bcrypt, logging)

### 4. **README.md** (201 lines)
- Comprehensive documentation for Manager application
- Database initialization instructions
- Environment variable reference
- Database schema documentation
- Security guidelines
- Troubleshooting section
- Development workflow guide

## Quick Start

```bash
# 1. Install dependencies
pip install -r /home/penguin/code/Nest/apps/manager/requirements.txt

# 2. Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=manager
export DB_USER=postgres
export DB_PASSWORD=your_secure_password
export SECRET_KEY=your_secret_key

# 3. Run initialization
cd /home/penguin/code/Nest/apps/manager
python db_init.py
```

## Resource Types Initialized (14 total)

### Storage (6 types)
- storage-iscsi: iSCSI Storage
- storage-nfs: NFS Network File System
- storage-scsi: SCSI Storage
- storage-sas: Serial Attached SCSI
- storage-san: Storage Area Network
- storage-ceph: Ceph Distributed Storage

### Database (6 types)
- db-mariadb: MariaDB Database
- db-galera: Galera Cluster
- db-postgresql: PostgreSQL Database
- db-redis: Redis Cache
- db-valkey: Valkey Cache
- db-sqlite: SQLite Database

### Big Data (2 types)
- bigdata-hadoop: Apache Hadoop
- bigdata-trino: Trino Query Engine

## Database Schema

The initialization creates 5 tables:

1. **role** - User roles for authentication
   - id, name, description, created_at

2. **user** - User accounts (Flask-Security-Too)
   - id, email, username, password, active, confirmed_at, created_at, updated_at

3. **roles_users** - User-role associations
   - id, user_id, role_id

4. **team** - Teams/organizations
   - id, name, description, is_global, created_at, updated_at

5. **resource_type** - Supported resource types
   - id, category, type_name, description, created_at

## Key Features

1. **Environment-based Configuration**: All database settings via environment variables
2. **Idempotent Operations**: Safe to run multiple times without errors
3. **Comprehensive Logging**: Detailed output for debugging
4. **Error Handling**: Proper exception handling and rollback on failures
5. **Verification**: Automatic verification of setup completion
6. **Success Summary**: Clear confirmation of what was initialized

## Important Notes

1. This script is for **initial setup only**
2. After initialization, use **PyDAL** for all database operations
3. Do NOT use SQLAlchemy directly after initial setup
4. The Global team cannot be deleted (foundational data)
5. Resource types are extensible via PyDAL models

## Post-Initialization

After running `db_init.py`, create PyDAL models in `models.py` for your application:

```python
# apps/manager/models.py
from pydal import DAL, Field
from .common import db

# Define your tables with PyDAL
db.define_table('resource',
    Field('name', 'string'),
    Field('type_id', 'reference resource_type'),
    Field('team_id', 'reference team'),
)
```

## Troubleshooting

See `/home/penguin/code/Nest/apps/manager/README.md` for comprehensive troubleshooting guidance.

## Summary

- **Total Lines**: 573 lines of code and documentation
- **Main Script**: 348 lines (db_init.py)
- **Documentation**: 201 lines (README.md)
- **Configuration**: 15 lines (requirements.txt)
- **Package**: 9 lines (__init__.py)
