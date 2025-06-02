import uuid
from sqlalchemy import Column, Integer, TIMESTAMP, Index, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .base import Base

class Regions(Base):
  __tablename__ = 'regions'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  page_shop_id = Column(String, nullable=False, index=True)
  image_path = Column(String, nullable=False, index=True)
  bbox = Column(JSONB, nullable=True)
  vector = Column(Vector(1024), nullable=True)
  phrase = Column(String, nullable=False)

  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    Index('idx_page_image', 'page_shop_id', 'image_path'),
    Index('idx_page_phrase_image', 'page_shop_id', 'phrase', 'image_path'),
  )

  def __repr__(self):
    return f"<Regions(id={self.id}, page_shop_id={self.page_shop_id}, image_path={self.image_path}, bbox={self.bbox}, vector={self.vector}, phrase={self.phrase})>"