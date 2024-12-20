"""Initial migration

Revision ID: 679202f4baab
Revises: 787fa3b11d3b
Create Date: 2024-10-23 10:38:15.644146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '679202f4baab'
down_revision: Union[str, None] = '787fa3b11d3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('news_categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_news_categories_id'), 'news_categories', ['id'], unique=False)
    op.create_table('news_articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('published_date', sa.Date(), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['category_id'], ['news_categories.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_index(op.f('ix_news_articles_id'), 'news_articles', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_news_articles_id'), table_name='news_articles')
    op.drop_table('news_articles')
    op.drop_index(op.f('ix_news_categories_id'), table_name='news_categories')
    op.drop_table('news_categories')
    # ### end Alembic commands ###
