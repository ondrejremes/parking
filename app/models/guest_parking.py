import uuid
from sqlalchemy import Date, DateTime, ForeignKey, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class GuestParking(Base):
    __tablename__ = "guest_parkings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spots.id"), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    time_from: Mapped[Time] = mapped_column(Time, nullable=False)
    time_to: Mapped[Time] = mapped_column(Time, nullable=False)
    guest_name: Mapped[str] = mapped_column(String(255), nullable=False)
    guest_plate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    spot = relationship("Spot")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
