import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, Index, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .base import Base

class Regions(Base):
  __tablename__ = 'regions'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  shop_id = Column(Integer, nullable=False, index=True)
  image_path = Column(String, nullable=False, index=True)
  bbox = Column(JSONB, nullable=False)
  vector = Column(Vector(1024), nullable=True)
  phrase = Column(String, nullable=True)

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    Index('idx_shop_image', 'shop_id', 'image_path'),
    Index('idx_shop_phrase_image', 'shop_id', 'phrase', 'image_path'),
  )

  def __repr__(self):
    return f"<Regions(id={self.id}, shop_id={self.shop_id}, image_path={self.image_path}, bbox={self.bbox}, vector={self.vector}, phrase={self.phrase})>"