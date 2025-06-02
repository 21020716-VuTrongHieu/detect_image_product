import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .base import Base

class VariationData(Base):
  __tablename__ = 'variation_data'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  page_shop_id = Column(String, nullable=False, index=True)
  product_id = Column(String, nullable=False, index=True)
  variation_id = Column(String, nullable=False, index=True)
  meta_data = Column(JSONB, nullable=True)

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    Index('idx_page_product', 'page_shop_id', 'product_id'),
    Index('idx_page_variation', 'page_shop_id', 'variation_id'),
    Index('idx_product_variation', 'product_id', 'variation_id'),
    Index('idx_page_product_variation', 'page_shop_id', 'product_id', 'variation_id'),
    UniqueConstraint('page_shop_id', 'product_id', 'variation_id', name='uq_variation_data_page_product_variation'),
  )

  def __repr__(self):
    return f"<VariationData(id={self.id}, page_shop_id={self.page_shop_id}, product_id={self.product_id}, variation_id={self.variation_id})>"