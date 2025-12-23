"""
Teams Model

Defines the teams table for organizing users and resources.
"""

from pydal.validators import IS_NOT_EMPTY


def define_teams(db):
    """Define the teams table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'teams',
        db.Field('name', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 unique=True,
                 comment='Team name'),
        db.Field('description', 'text',
                 comment='Team description'),
        db.Field('is_global', 'boolean',
                 default=False,
                 comment='Whether this is a global team'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),
        db.Field('updated_at', 'datetime',
                 default=db.current_timestamp,
                 update=db.current_timestamp,
                 comment='Last update timestamp'),
        db.Field('deleted_at', 'datetime',
                 comment='Soft delete timestamp'),

        # Indexes
        indexes=[
            ['name'],
            ['created_at'],
            ['is_global'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(name)s'
    )
