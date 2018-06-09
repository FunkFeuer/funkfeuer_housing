"""unify payment_type between invoice and payment

Revision ID: c35af4b87c11
Revises: 4150631d7bbe
Create Date: 2018-06-01 23:38:16.666750

"""
from alembic import op
import sqlalchemy as sa


revision = 'c35af4b87c11'
down_revision = '4150631d7bbe'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payment', sa.Column('payment_type', sa.Enum('SEPA-DD', 'money transfer', 'cash_payment', name='payment_types'), nullable=True))
    op.drop_column('payment', 'paymenttype')


def downgrade():
    op.add_column('payment', sa.Column('paymenttype', sa.VARCHAR(length=32), autoincrement=False, nullable=True))
    op.drop_column('payment', 'payment_type')
