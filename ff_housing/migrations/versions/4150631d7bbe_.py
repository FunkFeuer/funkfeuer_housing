""" add sepa fields
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4150631d7bbe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('sepa_mandate_id', sa.Unicode(length=32), nullable=True))
    op.add_column('user', sa.Column('sepa_mandate_date', sa.Date(), nullable=True))
    op.add_column('user', sa.Column('sepa_mandate_first', sa.Boolean(), nullable=True))
    op.add_column('invoice', sa.Column('exported_id', sa.Unicode(length=35), nullable=True))
    op.create_unique_constraint(None, 'user', ['sepa_mandate_id'])
    op.execute('UPDATE "user" SET sepa_mandate_first=FALSE')
    op.alter_column('user', 'sepa_mandate_first', nullable=False)
    op.drop_column('user', 'sepa_mandate')
    op.drop_constraint('user_sepa_mandate_key', 'user', type_='unique')


def downgrade():
    op.add_column('user', sa.Column('sepa_mandate', sa.VARCHAR(length=32), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'user', type_='unique')
    op.create_unique_constraint('user_sepa_mandate_key', 'user', ['sepa_mandate'])
    op.drop_column('user', 'sepa_mandate_id')
    op.drop_column('user', 'sepa_mandate_date')
    op.drop_column('user', 'sepa_mandate_first')
    op.drop_column('invoice', 'exported_id')
