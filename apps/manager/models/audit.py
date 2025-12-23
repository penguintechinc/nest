"""
Audit Log Model

Defines audit logging for compliance and security monitoring.
"""

from pydal.validators import IS_NOT_EMPTY


def define_audit_logs(db):
    """Define the audit_logs table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'audit_logs',
        db.Field('user_id', 'reference users',
                 comment='User who performed the action'),
        db.Field('action', 'string',
                 length=100,
                 requires=IS_NOT_EMPTY(),
                 comment='Action performed'),
        db.Field('resource_type', 'string',
                 length=100,
                 comment='Type of resource affected'),
        db.Field('resource_id', 'integer',
                 comment='ID of resource affected'),
        db.Field('team_id', 'reference teams',
                 comment='Team context for the action'),
        db.Field('details', 'json',
                 comment='Additional action details'),
        db.Field('ip_address', 'string',
                 length=45,
                 comment='IP address of client'),
        db.Field('user_agent', 'text',
                 comment='User agent string'),
        db.Field('timestamp', 'datetime',
                 default=db.current_timestamp,
                 comment='Action timestamp'),

        indexes=[
            ['user_id'],
            ['timestamp'],
            ['action'],
            ['resource_type'],
            ['team_id'],
            ['user_id', 'timestamp'],
            ['resource_type', 'resource_id'],
        ],

        migrate=True,
        fake_migrate=False,
    )
