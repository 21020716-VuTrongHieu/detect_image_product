import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base

class ImagesShop(Base):
  __tablename__ = 'images_shop'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  shop_id = Column(Integer, nullable=False, index=True)
  image_url = Column(String, nullable=False, index=True)

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    Index('idx_shop_image', 'shop_id', 'image_url'),
  )

  def __repr__(self):
    return f"<ImagesShop(id={self.id}, shop_id={self.shop_id}, image_url={self.image_url})>"