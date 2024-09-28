"""Auto-generated migration

Revision ID: 0c79774765ce
Revises: f08283fac8da
Create Date: 2024-09-28 15:27:30.503842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c79774765ce'
down_revision: Union[str, None] = 'f08283fac8da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_KB_REGION_id', table_name='KB_REGION')
    op.drop_index('ix_KB_REGION_region_name', table_name='KB_REGION')
    op.drop_table('KB_REGION')
    op.drop_index('ix_KB_PREDICTION_date', table_name='KB_PREDICTION')
    op.drop_index('ix_KB_PREDICTION_id', table_name='KB_PREDICTION')
    op.drop_table('KB_PREDICTION')
    op.drop_index('ix_KB_PROPERTY_PRICE_DATA_date', table_name='KB_PROPERTY_PRICE_DATA')
    op.drop_index('ix_KB_PROPERTY_PRICE_DATA_id', table_name='KB_PROPERTY_PRICE_DATA')
    op.drop_index('ix_KB_PROPERTY_PRICE_DATA_price_type', table_name='KB_PROPERTY_PRICE_DATA')
    op.drop_index('ix_KB_PROPERTY_PRICE_DATA_time_span', table_name='KB_PROPERTY_PRICE_DATA')
    op.drop_table('KB_PROPERTY_PRICE_DATA')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('KB_PROPERTY_PRICE_DATA',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('region_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('price_type', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('time_span', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('index_value', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('avg_price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='KB_PROPERTY_PRICE_DATA_pkey')
    )
    op.create_index('ix_KB_PROPERTY_PRICE_DATA_time_span', 'KB_PROPERTY_PRICE_DATA', ['time_span'], unique=False)
    op.create_index('ix_KB_PROPERTY_PRICE_DATA_price_type', 'KB_PROPERTY_PRICE_DATA', ['price_type'], unique=False)
    op.create_index('ix_KB_PROPERTY_PRICE_DATA_id', 'KB_PROPERTY_PRICE_DATA', ['id'], unique=False)
    op.create_index('ix_KB_PROPERTY_PRICE_DATA_date', 'KB_PROPERTY_PRICE_DATA', ['date'], unique=False)
    op.create_table('KB_PREDICTION',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('region_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('price_type', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('time_span', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('predicted_value', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='KB_PREDICTION_pkey')
    )
    op.create_index('ix_KB_PREDICTION_id', 'KB_PREDICTION', ['id'], unique=False)
    op.create_index('ix_KB_PREDICTION_date', 'KB_PREDICTION', ['date'], unique=False)
    op.create_table('KB_REGION',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('region_name', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='KB_REGION_pkey')
    )
    op.create_index('ix_KB_REGION_region_name', 'KB_REGION', ['region_name'], unique=True)
    op.create_index('ix_KB_REGION_id', 'KB_REGION', ['id'], unique=False)
    # ### end Alembic commands ###