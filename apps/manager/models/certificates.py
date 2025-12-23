"""
Certificates Models

Defines certificate authorities and certificates for TLS/encryption.
"""

from pydal.validators import IS_NOT_EMPTY, IS_IN_SET


def define_certificate_authorities(db):
    """Define the certificate_authorities table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'certificate_authorities',
        db.Field('name', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='CA name'),
        db.Field('type', 'string',
                 length=50,
                 requires=IS_IN_SET(['root', 'intermediate', 'self_signed']),
                 comment='Certificate Authority type'),
        db.Field('certificate', 'text',
                 requires=IS_NOT_EMPTY(),
                 comment='PEM-encoded certificate'),
        db.Field('private_key', 'text',
                 comment='PEM-encoded private key'),
        db.Field('subject', 'string',
                 length=500,
                 comment='Certificate subject'),
        db.Field('issuer', 'string',
                 length=500,
                 comment='Certificate issuer'),
        db.Field('valid_from', 'datetime',
                 comment='Certificate validity start'),
        db.Field('valid_until', 'datetime',
                 comment='Certificate validity end'),
        db.Field('serial_number', 'string',
                 length=255,
                 comment='Certificate serial number'),
        db.Field('is_nest_managed', 'boolean',
                 default=True,
                 comment='Whether NEST manages this CA'),
        db.Field('created_by', 'reference users',
                 comment='User who created this CA'),
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
            ['type'],
            ['serial_number'],
            ['created_at'],
            ['is_nest_managed'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(name)s'
    )


def define_certificates(db):
    """Define the certificates table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'certificates',
        db.Field('resource_id', 'reference resources',
                 ondelete='CASCADE',
                 comment='Resource reference'),
        db.Field('ca_id', 'reference certificate_authorities',
                 requires=IS_NOT_EMPTY(),
                 comment='Issuing CA reference'),
        db.Field('certificate', 'text',
                 requires=IS_NOT_EMPTY(),
                 comment='PEM-encoded certificate'),
        db.Field('private_key', 'text',
                 requires=IS_NOT_EMPTY(),
                 comment='PEM-encoded private key'),
        db.Field('common_name', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='Certificate common name (CN)'),
        db.Field('san_dns', 'json',
                 comment='Subject Alternative Names (DNS)'),
        db.Field('san_ips', 'json',
                 comment='Subject Alternative Names (IP addresses)'),
        db.Field('valid_from', 'datetime',
                 comment='Certificate validity start'),
        db.Field('valid_until', 'datetime',
                 comment='Certificate validity end'),
        db.Field('serial_number', 'string',
                 length=255,
                 comment='Certificate serial number'),
        db.Field('auto_renew', 'boolean',
                 default=True,
                 comment='Whether to auto-renew certificate'),
        db.Field('renewal_threshold_days', 'integer',
                 default=30,
                 comment='Days before expiry to trigger renewal'),
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
            ['ca_id'],
            ['common_name'],
            ['serial_number'],
            ['valid_until'],
            ['created_at'],
            ['auto_renew'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(common_name)s'
    )
