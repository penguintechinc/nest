"""
NEST Manager Models - PyDAL Database Layer

Initializes PostgreSQL connection and imports all model definitions.
Uses environment variables for database configuration.
"""

import os
from datetime import datetime
from pydal import DAL, Field
from pydal.validators import IS_NOT_EMPTY, IS_EMAIL, IS_INT_IN_RANGE, CLEANUP

# Database connection configuration from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'nest')
DB_USER = os.getenv('DB_USER', 'nest')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'nest')

# Construct PostgreSQL connection string
DB_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

# Initialize DAL instance
db = DAL(
    DB_URI,
    pool_size=10,
    migrate=True,
    fake_migrate=False,
    auto_import=False,
    check_reserved=['all']
)

# Import all model definitions
from .teams import define_teams
from .users import define_users, define_team_memberships
from .resources import (
    define_resource_types,
    define_resources,
    define_resource_users,
    define_resource_stats,
    define_backup_jobs,
    define_provisioning_jobs
)
from .certificates import define_certificate_authorities, define_certificates
from .audit import define_audit_logs

# Define all tables
define_teams(db)
define_users(db)
define_team_memberships(db)
define_resource_types(db)
define_resources(db)
define_resource_users(db)
define_resource_stats(db)
define_backup_jobs(db)
define_provisioning_jobs(db)
define_certificate_authorities(db)
define_certificates(db)
define_audit_logs(db)

# Commit schema if needed
db.commit()

__all__ = [
    'db',
    'DB_URI',
    'DB_HOST',
    'DB_PORT',
    'DB_NAME',
    'DB_USER',
]
