"""add power_outlet endpoint and switchable boolean

Revision ID: 4ceec83f3a61
Revises: 5cc4c8c6ac0b
Create Date: 2018-06-21 23:25:53.650596

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ceec83f3a61'
down_revision = 'c35af4b87c11'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('power_outlet', sa.Column('endpoint', sa.Unicode(length=128), nullable=False))
    op.create_unique_constraint(None, 'power_outlet', ['endpoint'])
    op.add_column('power_outlet', sa.Column('switchable', sa.Boolean(), nullable=True))
    op.execute('UPDATE "power_outlet" SET switchable=TRUE')
    op.alter_column('power_outlet', 'switchable', nullable=False)


def downgrade():
    op.drop_column('power_outlet', 'endpoint')
    op.drop_column('power_outlet', 'switchable')
