"""
Resources Models

Defines resource types, resources, resource users, and related operational models.
"""

from pydal.validators import IS_NOT_EMPTY, IS_IN_SET


def define_resource_types(db):
    """Define the resource_types table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'resource_types',
        db.Field('name', 'string',
                 length=100,
                 requires=IS_NOT_EMPTY(),
                 unique=True,
                 comment='Resource type identifier'),
        db.Field('category', 'string',
                 length=50,
                 requires=IS_NOT_EMPTY(),
                 comment='Resource category (compute, storage, network, etc)'),
        db.Field('display_name', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='Human-readable display name'),
        db.Field('icon', 'string',
                 length=100,
                 comment='Icon identifier/URL'),
        db.Field('supports_full_lifecycle', 'boolean',
                 default=True,
                 comment='Supports full lifecycle management'),
        db.Field('supports_partial_lifecycle', 'boolean',
                 default=True,
                 comment='Supports partial lifecycle management'),
        db.Field('supports_user_management', 'boolean',
                 default=False,
                 comment='Supports user/credential management'),
        db.Field('supports_backup', 'boolean',
                 default=False,
                 comment='Supports backup operations'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),

        indexes=[
            ['name'],
            ['category'],
            ['created_at'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(display_name)s'
    )


def define_resources(db):
    """Define the resources table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'resources',
        db.Field('name', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='Resource name'),
        db.Field('resource_type_id', 'reference resource_types',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource type reference'),
        db.Field('team_id', 'reference teams',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Team that owns this resource'),
        db.Field('status', 'string',
                 length=50,
                 default='pending',
                 requires=IS_IN_SET(['pending', 'provisioning', 'active',
                                     'updating', 'paused', 'error', 'deleted']),
                 comment='Resource status'),
        db.Field('lifecycle_mode', 'string',
                 length=50,
                 requires=IS_NOT_EMPTY(),
                 comment='Lifecycle mode (full, partial, import)'),
        db.Field('provisioning_method', 'string',
                 length=50,
                 comment='Method used for provisioning'),
        db.Field('connection_info', 'json',
                 comment='Connection information (host, port, etc)'),
        db.Field('credentials', 'json',
                 comment='Encrypted credentials'),
        db.Field('tls_enabled', 'boolean',
                 default=False,
                 comment='Whether TLS is enabled'),
        db.Field('tls_ca_id', 'reference certificate_authorities',
                 comment='TLS CA certificate reference'),
        db.Field('tls_cert_id', 'reference certificates',
                 comment='TLS certificate reference'),
        db.Field('k8s_namespace', 'string',
                 length=255,
                 comment='Kubernetes namespace'),
        db.Field('k8s_resource_name', 'string',
                 length=255,
                 comment='Kubernetes resource name'),
        db.Field('k8s_resource_type', 'string',
                 length=50,
                 comment='Kubernetes resource type (pod, deployment, etc)'),
        db.Field('config', 'json',
                 comment='Resource-specific configuration'),
        db.Field('can_modify_users', 'boolean',
                 default=False,
                 comment='Whether users can be modified'),
        db.Field('can_modify_config', 'boolean',
                 default=False,
                 comment='Whether configuration can be modified'),
        db.Field('can_backup', 'boolean',
                 default=False,
                 comment='Whether backups are enabled'),
        db.Field('can_scale', 'boolean',
                 default=False,
                 comment='Whether resource can be scaled'),
        db.Field('created_by', 'reference users',
                 comment='User who created this resource'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),
        db.Field('updated_at', 'datetime',
                 default=db.current_timestamp,
                 update=db.current_timestamp,
                 comment='Last update timestamp'),
        db.Field('deleted_at', 'datetime',
                 comment='Soft delete timestamp'),

        indexes=[
            ['name'],
            ['team_id'],
            ['resource_type_id'],
            ['status'],
            ['created_at'],
            ['team_id', 'name'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(name)s'
    )


def define_resource_users(db):
    """Define the resource_users table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'resource_users',
        db.Field('resource_id', 'reference resources',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource reference'),
        db.Field('username', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='Username on resource'),
        db.Field('password_hash', 'string',
                 length=255,
                 comment='Encrypted password hash'),
        db.Field('roles', 'json',
                 comment='Roles assigned to user'),
        db.Field('sync_status', 'string',
                 length=50,
                 default='pending',
                 requires=IS_IN_SET(['pending', 'syncing', 'synced', 'error']),
                 comment='Synchronization status'),
        db.Field('last_synced_at', 'datetime',
                 comment='Last successful sync timestamp'),
        db.Field('sync_error', 'text',
                 comment='Last synchronization error message'),
        db.Field('created_by', 'reference users',
                 comment='User who created this resource user'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),
        db.Field('updated_at', 'datetime',
                 default=db.current_timestamp,
                 update=db.current_timestamp,
                 comment='Last update timestamp'),
        db.Field('deleted_at', 'datetime',
                 comment='Soft delete timestamp'),

        indexes=[
            ['resource_id'],
            ['resource_id', 'username'],
            ['sync_status'],
            ['created_at'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(username)s'
    )


def define_resource_stats(db):
    """Define the resource_stats table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'resource_stats',
        db.Field('resource_id', 'reference resources',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource reference'),
        db.Field('timestamp', 'datetime',
                 default=db.current_timestamp,
                 comment='Metrics timestamp'),
        db.Field('metrics', 'json',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource metrics data'),
        db.Field('risk_level', 'string',
                 length=20,
                 comment='Risk assessment level (low, medium, high, critical)'),
        db.Field('risk_factors', 'json',
                 comment='Risk assessment factors'),

        indexes=[
            ['resource_id'],
            ['timestamp'],
            ['resource_id', 'timestamp'],
        ],

        migrate=True,
        fake_migrate=False,
    )


def define_backup_jobs(db):
    """Define the backup_jobs table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'backup_jobs',
        db.Field('resource_id', 'reference resources',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource reference'),
        db.Field('job_type', 'string',
                 length=50,
                 requires=IS_NOT_EMPTY(),
                 comment='Type of backup job'),
        db.Field('status', 'string',
                 length=50,
                 default='pending',
                 requires=IS_IN_SET(['pending', 'running', 'completed',
                                     'failed', 'cancelled']),
                 comment='Job status'),
        db.Field('backup_location', 'text',
                 comment='Location where backup is stored'),
        db.Field('backup_size_bytes', 'bigint',
                 comment='Size of backup in bytes'),
        db.Field('started_at', 'datetime',
                 comment='Job start timestamp'),
        db.Field('completed_at', 'datetime',
                 comment='Job completion timestamp'),
        db.Field('error_message', 'text',
                 comment='Error message if job failed'),
        db.Field('created_by', 'reference users',
                 comment='User who created this backup job'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),

        indexes=[
            ['resource_id'],
            ['status'],
            ['created_at'],
            ['resource_id', 'created_at'],
        ],

        migrate=True,
        fake_migrate=False,
    )


def define_provisioning_jobs(db):
    """Define the provisioning_jobs table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'provisioning_jobs',
        db.Field('resource_id', 'reference resources',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Resource reference'),
        db.Field('job_type', 'string',
                 length=50,
                 requires=IS_NOT_EMPTY(),
                 comment='Type of provisioning job'),
        db.Field('status', 'string',
                 length=50,
                 default='pending',
                 requires=IS_IN_SET(['pending', 'running', 'completed',
                                     'failed', 'rolled_back']),
                 comment='Job status'),
        db.Field('started_at', 'datetime',
                 comment='Job start timestamp'),
        db.Field('completed_at', 'datetime',
                 comment='Job completion timestamp'),
        db.Field('logs', 'text',
                 comment='Job execution logs'),
        db.Field('error_message', 'text',
                 comment='Error message if job failed'),
        db.Field('created_by', 'reference users',
                 comment='User who created this provisioning job'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),
        db.Field('updated_at', 'datetime',
                 default=db.current_timestamp,
                 update=db.current_timestamp,
                 comment='Last update timestamp'),

        indexes=[
            ['resource_id'],
            ['status'],
            ['created_at'],
            ['resource_id', 'created_at'],
        ],

        migrate=True,
        fake_migrate=False,
    )
