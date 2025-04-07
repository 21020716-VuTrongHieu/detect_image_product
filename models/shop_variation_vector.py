import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, Index, String, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .base import Base

class ShopVariationVector(Base):
  __tablename__ = 'shop_variation_vector'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  product_id = Column(String, nullable=False, index=True)
  variation_id = Column(String, nullable=False, index=True)
  shop_id = Column(Integer, nullable=False, index=True)
  vector = Column(Vector(768), nullable=False)
  meta_data = Column(JSONB, nullable=True)
  phrase = Column(String, nullable=True)
  logit = Column(Float, nullable=True)
  bounding_box = Column(JSONB, nullable=True)

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    Index('idx_shop_variation', 'shop_id', 'variation_id'),
    Index('idx_shop_product', 'shop_id', 'product_id'),
    Index('idx_product_variation', 'product_id', 'variation_id'),
    Index('idx_shop_product_variation', 'shop_id', 'product_id', 'variation_id'),
  )

  def __repr__(self):
    return f"<ShopVariationVector(id={self.id}, product_id={self.product_id}, variation_id={self.variation_id}, shop_id={self.shop_id})>"