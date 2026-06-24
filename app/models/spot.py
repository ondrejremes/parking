import uuid
from sqlalchemy import Boolean, String, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.enums import SpotType


class Spot(Base):
    __tablename__ = "spots"
    __table_args__ = (UniqueConstraint("floor", "number", name="uq_spots_floor_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    floor: Mapped[str] = mapped_column(String(20), nullable=False)
    number: Mapped[str] = mapped_column(String(20), nullable=False)
    spot_type: Mapped[SpotType] = mapped_column(SAEnum(SpotType, name="spottype"), nullable=False)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
