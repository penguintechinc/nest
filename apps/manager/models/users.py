"""
Users and Team Memberships Models

Defines users and their team membership relationships.
"""

from pydal.validators import IS_NOT_EMPTY, IS_EMAIL


def define_users(db):
    """Define the users table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'users',
        db.Field('username', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 unique=True,
                 comment='Unique username'),
        db.Field('email', 'string',
                 length=255,
                 requires=[IS_NOT_EMPTY(), IS_EMAIL()],
                 unique=True,
                 comment='User email address'),
        db.Field('password_hash', 'string',
                 length=255,
                 requires=IS_NOT_EMPTY(),
                 comment='Hashed password'),
        db.Field('first_name', 'string',
                 length=255,
                 comment='User first name'),
        db.Field('last_name', 'string',
                 length=255,
                 comment='User last name'),
        db.Field('is_active', 'boolean',
                 default=True,
                 comment='Whether user account is active'),
        db.Field('last_login_at', 'datetime',
                 comment='Last login timestamp'),
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
            ['username'],
            ['email'],
            ['created_at'],
            ['is_active'],
        ],

        migrate=True,
        fake_migrate=False,
        format='%(username)s'
    )


def define_team_memberships(db):
    """Define the team_memberships table.

    Args:
        db: PyDAL DAL instance
    """
    db.define_table(
        'team_memberships',
        db.Field('user_id', 'reference users',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Reference to user'),
        db.Field('team_id', 'reference teams',
                 ondelete='CASCADE',
                 requires=IS_NOT_EMPTY(),
                 comment='Reference to team'),
        db.Field('role', 'string',
                 length=50,
                 requires=IS_NOT_EMPTY(),
                 comment='User role in team (admin, member, viewer)'),
        db.Field('created_at', 'datetime',
                 default=db.current_timestamp,
                 comment='Creation timestamp'),
        db.Field('updated_at', 'datetime',
                 default=db.current_timestamp,
                 update=db.current_timestamp,
                 comment='Last update timestamp'),

        # Indexes
        indexes=[
            ['user_id'],
            ['team_id'],
            ['user_id', 'team_id'],  # Unique constraint via composite index
        ],

        migrate=True,
        fake_migrate=False,
        format='%(role)s'
    )
