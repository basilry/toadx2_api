"""Auto-generated migration

Revision ID: 05f5f491f8be
Revises: 0a64d5aba7b3
Create Date: 2024-10-03 20:14:38.571435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05f5f491f8be'
down_revision: Union[str, None] = '0a64d5aba7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('legal_dong_code',
    sa.Column('code', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('code')
    )
    op.create_index(op.f('ix_legal_dong_code_code'), 'legal_dong_code', ['code'], unique=False)
    op.create_index(op.f('ix_legal_dong_code_name'), 'legal_dong_code', ['name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_legal_dong_code_name'), table_name='legal_dong_code')
    op.drop_index(op.f('ix_legal_dong_code_code'), table_name='legal_dong_code')
    op.drop_table('legal_dong_code')
    # ### end Alembic commands ###
