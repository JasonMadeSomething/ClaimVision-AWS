from sqlalchemy import Column, String, UUID, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from models.base import Base

class Label(Base):
    """✅ Represents a shared label that can be linked to multiple files."""
    __tablename__ = "labels"

    id: Mapped[uuid.UUID] = Column(UUID, primary_key=True, default=uuid.uuid4)
    label_text: Mapped[str] = Column(String, nullable=False, )  
    is_ai_generated: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    deleted: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    household_id: Mapped[uuid.UUID] = Column(UUID, ForeignKey("households.id"), nullable=False)  # ✅ Enforces ownership
    household = relationship("Household")

    files = relationship("File", secondary="file_labels", back_populates="labels")

    __table_args__ = (
        UniqueConstraint('label_text', 'is_ai_generated', 'household_id', name='label_text_is_ai_generated_unique'),
    )
    def to_dict(self):
        return {
            "id": str(self.id),
            "label_text": self.label_text,
            "is_ai_generated": self.is_ai_generated,
            "deleted": self.deleted
        }