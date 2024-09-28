"""Auto-generated migration

Revision ID: c26a2ce4d657
Revises: 7a463d6008d0
Create Date: 2024-09-28 15:49:51.602254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c26a2ce4d657'
down_revision: Union[str, None] = '7a463d6008d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('kb_property_price_data', sa.Column('avg_price', sa.Float(), nullable=True))
    op.drop_column('kb_property_price_data', 'avg_price1')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('kb_property_price_data', sa.Column('avg_price1', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.drop_column('kb_property_price_data', 'avg_price')
    # ### end Alembic commands ###