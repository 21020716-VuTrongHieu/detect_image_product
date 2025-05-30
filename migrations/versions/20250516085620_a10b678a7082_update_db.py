"""update db

Revision ID: 20250516085620_a10b678a7082
Revises: 20250515035736_4c9c9a3f3956
Create Date: 2025-05-16 08:56:20.678730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250516085620_a10b678a7082'
down_revision: Union[str, None] = '20250515035736_4c9c9a3f3956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Upgrade schema."""
  # ### commands auto generated by Alembic - please adjust! ###
  op.drop_index('idx_shop_region', table_name='regions')
  op.create_index('idx_shop_phrase_image', 'regions', ['shop_id', 'phrase', 'image_path'], unique=False)
  op.drop_column('regions', 'region_key')
  # ### end Alembic commands ###


def downgrade() -> None:
  """Downgrade schema."""
  # ### commands auto generated by Alembic - please adjust! ###
  op.add_column('regions', sa.Column('region_key', sa.VARCHAR(), autoincrement=False, nullable=False))
  op.drop_index('idx_shop_phrase_image', table_name='regions')
  op.create_index('idx_shop_region', 'regions', ['shop_id', 'region_key'], unique=False)
  # ### end Alembic commands ###
