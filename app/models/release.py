import uuid
from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base
from app.models.enums import Shift, ReleaseType


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spots.id"), nullable=False)
    date: Mapped[Date] = mapped_column(Date, nullable=False)
    shift: Mapped[Shift] = mapped_column(SAEnum(Shift, name="shift"), nullable=False)
    release_type: Mapped[ReleaseType] = mapped_column(SAEnum(ReleaseType, name="releasetype"), nullable=False)
    transfer_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    retracted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    spot = relationship("Spot")
    transfer_to_user = relationship("User", foreign_keys=[transfer_to_user_id])
