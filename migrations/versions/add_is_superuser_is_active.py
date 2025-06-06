"""
Alembic migration: add is_superuser and is_active to users
"""

# revision identifiers, used by Alembic.
revision = 'add_is_superuser_is_active'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))

def downgrade():
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'is_active')
