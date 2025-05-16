from sqlalchemy import Column, TIMESTAMP, Index, ForeignKey, PrimaryKeyConstraint, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base

class VariationRegions(Base):
  __tablename__ = 'variation_regions'

  shop_id = Column(Integer, nullable=False, index=True)
  variation_data_id = Column(
    UUID(as_uuid=True),
    ForeignKey('variation_data.id', ondelete='CASCADE'),
    nullable=False,
    index=True
  )
  region_id = Column(
    UUID(as_uuid=True),
    ForeignKey('regions.id', ondelete='CASCADE'),
    nullable=False,
    index=True
  )

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    PrimaryKeyConstraint(
      'variation_data_id',
      'region_id',
      name='pk_variation_regions'
    ),
    Index('idx_variation_region', 'region_id', 'variation_data_id'),
    Index('idx_variation_region_shop', 'shop_id', 'region_id', 'variation_data_id'),
    Index('idx_variation_region_shop_variation', 'shop_id', 'variation_data_id'),
    Index('idx_variation_region_shop_region', 'shop_id', 'region_id')
  )

  def __repr__(self):
    return f"<VariationRegions(id={self.id}, variation_data_id={self.variation_data_id}, region_id={self.region_id})>"