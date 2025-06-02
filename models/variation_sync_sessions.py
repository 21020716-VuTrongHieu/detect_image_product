import uuid
from sqlalchemy import Column, Integer, Text, TIMESTAMP, Index, CheckConstraint, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .base import Base

class VariationSyncSessions(Base):
  __tablename__ = 'variation_sync_sessions'

  id = Column(UUID, primary_key=True, default=uuid.uuid4)
  page_id = Column(String, nullable=False, index=True)
  total_variations = Column(Integer, nullable=False, default=0)
  processed_variations = Column(Integer, nullable=False, default=0)
  error_count = Column(Integer, nullable=False, default=0)
  status = Column(
    Text,
    nullable=False,
    default='pending',
  )
  created_at = Column(TIMESTAMP, server_default=func.now())
  updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

  __table_args__ = (
    CheckConstraint(
      "status IN ('pending', 'in_progress', 'completed', 'failed')",
      name='chk_variationsync_status'
    ),
    Index('idx_page_status', 'page_id', 'status'),
  )

  def __repr__(self):
    return f"<VariationSyncSessions(id={self.id}, page_id={self.page_id}, total_variations={self.total_variations}, processed_variations={self.processed_variations}, error_count={self.error_count}, status={self.status})>"