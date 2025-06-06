"""
Alembic migration: add is_superuser and is_active to users
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade():
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')
