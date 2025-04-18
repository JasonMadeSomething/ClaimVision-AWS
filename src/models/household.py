from sqlalchemy import Column, String, UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
import uuid
from models.base import Base  # ✅ Restored Base import

class Household(Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)

    users = relationship("User", back_populates="household")
    claims = relationship("Claim", back_populates="household")
    files = relationship("File", back_populates="household")
    rooms = relationship("Room", back_populates="household", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name
        }
