# Manager Application

The Manager application handles resource management and orchestration for the Nest infrastructure.

## Database Initialization

### Initial Setup

The Manager application uses **Flask-Security-Too** and **SQLAlchemy** for initial database setup only. After initialization, all database operations use **PyDAL**.

#### Prerequisites

1. PostgreSQL must be running and accessible
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Running Database Initialization

Set environment variables and run the initialization script:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=manager
export DB_USER=postgres
export DB_PASSWORD=your_secure_password
export SECRET_KEY=your_secret_key

python db_init.py
```

#### What Gets Created

The initialization script creates:

1. **Database Tables**
   - `user`: User accounts (Flask-Security-Too integration)
   - `role`: User roles
   - `roles_users`: User-role associations
   - `team`: Resource teams
   - `resource_type`: Supported resource types

2. **Default Global Team**
   - Name: "Global"
   - is_global: TRUE
   - Description: "Global default team for all resources"

3. **Resource Types** (14 types across 3 categories)
   
   **Storage** (6 types):
   - storage-iscsi
   - storage-nfs
   - storage-scsi
   - storage-sas
   - storage-san
   - storage-ceph

   **Database** (6 types):
   - db-mariadb
   - db-galera
   - db-postgresql
   - db-redis
   - db-valkey
   - db-sqlite

   **Big Data** (2 types):
   - bigdata-hadoop
   - bigdata-trino

### Post-Initialization

**IMPORTANT**: After the initial database setup is complete, do NOT use SQLAlchemy or Flask-Security-Too directly for database operations.

All future database operations should use **PyDAL** as defined in the project standards. Create a `models.py` file in your application to define PyDAL models.

#### Environment Variables

The application uses the following environment variables for database configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| DB_HOST | localhost | PostgreSQL host |
| DB_PORT | 5432 | PostgreSQL port |
| DB_NAME | manager | Database name |
| DB_USER | postgres | Database user |
| DB_PASSWORD | (required) | Database password |
| SECRET_KEY | change-me-in-production | Flask secret key |

## Architecture

```
manager/
├── __init__.py          # Package initialization
├── db_init.py          # Database initialization script (Flask-SQLAlchemy)
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── models.py           # PyDAL models (to be created)
├── app.py              # Main application (to be created)
└── config.py           # Configuration management (to be created)
```

## Database Schema

### User Model
- `id`: Primary key
- `email`: Unique email address
- `username`: Unique username
- `password`: Hashed password
- `active`: Account status
- `confirmed_at`: Email confirmation timestamp
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp
- `roles`: Many-to-many relationship with Role

### Role Model
- `id`: Primary key
- `name`: Unique role name
- `description`: Role description
- `created_at`: Creation timestamp
- `users`: Many-to-many relationship with User

### Team Model
- `id`: Primary key
- `name`: Team name
- `description`: Team description
- `is_global`: Boolean flag for global team
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### ResourceType Model
- `id`: Primary key
- `category`: Resource category (storage, database, bigdata)
- `type_name`: Unique resource type identifier
- `description`: Resource type description
- `created_at`: Creation timestamp

## Security Notes

1. The `db_init.py` script requires the `DB_PASSWORD` environment variable
2. Always use strong passwords in production
3. Change the `SECRET_KEY` environment variable in production
4. Database user should have limited permissions (create/read/write to the manager database only)
5. Use TLS connections to PostgreSQL in production (SSL)

## Troubleshooting

### Connection Errors

If you get a database connection error:

```bash
# Verify PostgreSQL is running
psql -h localhost -U postgres -d postgres -c "SELECT 1"

# Check connection string
psql postgresql://user:password@localhost:5432/manager
```

### Missing Environment Variables

The script will fail if `DB_PASSWORD` is not set:

```bash
# Verify all required variables are set
env | grep DB_
```

### Permission Errors

Ensure the PostgreSQL user has permissions to create tables:

```bash
# Connect as postgres superuser
psql -U postgres

# Grant permissions
CREATE ROLE manager_user WITH LOGIN PASSWORD 'password';
GRANT ALL ON DATABASE manager TO manager_user;
```

### Already Initialized

If you run the script multiple times, it safely checks for existing data:
- Existing Global team will not be duplicated
- Existing resource types will be skipped
- Idempotent operation for safety

## Development Workflow

1. **Initial Setup**: Run `python db_init.py` once
2. **Model Development**: Define PyDAL models in `models.py`
3. **Database Changes**: Use PyDAL's migration features or manual SQL
4. **Testing**: Ensure tests use isolated databases or transactions

## See Also

- [CLAUDE.md](../../CLAUDE.md) - Project standards and guidelines
- [Architecture Documentation](../../docs/architecture/) - System architecture
- [Database Documentation](../../docs/database/) - Database guide
