"""update db

Revision ID: 20250515035736_4c9c9a3f3956
Revises: 20250513185824_e8f761c43f36
Create Date: 2025-05-15 03:57:36.215046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250515035736_4c9c9a3f3956'
down_revision: Union[str, None] = '20250513185824_e8f761c43f36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  """Upgrade schema."""
  # ### commands auto generated by Alembic - please adjust! ###
  op.drop_constraint('uq_regions_shop_image_region_key', 'regions', type_='unique')
  op.add_column('variation_regions', sa.Column('shop_id', sa.Integer(), nullable=False))
  op.drop_index('idx_variation_region', table_name='variation_regions')
  op.create_index('idx_variation_region', 'variation_regions', ['region_id', 'variation_data_id'], unique=False)
  op.create_index('idx_variation_region_shop', 'variation_regions', ['shop_id', 'region_id', 'variation_data_id'], unique=False)
  op.create_index('idx_variation_region_shop_region', 'variation_regions', ['shop_id', 'region_id'], unique=False)
  op.create_index('idx_variation_region_shop_variation', 'variation_regions', ['shop_id', 'variation_data_id'], unique=False)
  op.create_index(op.f('ix_variation_regions_shop_id'), 'variation_regions', ['shop_id'], unique=False)
  # ### end Alembic commands ###


def downgrade() -> None:
  """Downgrade schema."""
  # ### commands auto generated by Alembic - please adjust! ###
  op.drop_index(op.f('ix_variation_regions_shop_id'), table_name='variation_regions')
  op.drop_index('idx_variation_region_shop_variation', table_name='variation_regions')
  op.drop_index('idx_variation_region_shop_region', table_name='variation_regions')
  op.drop_index('idx_variation_region_shop', table_name='variation_regions')
  op.drop_index('idx_variation_region', table_name='variation_regions')
  op.create_index('idx_variation_region', 'variation_regions', ['variation_data_id', 'region_id'], unique=False)
  op.drop_column('variation_regions', 'shop_id')
  op.create_unique_constraint('uq_regions_shop_image_region_key', 'regions', ['shop_id', 'image_path', 'region_key'])
  # ### end Alembic commands ###
