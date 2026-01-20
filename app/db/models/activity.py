from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # The level is maintained by a DB trigger (1..3). Level 1 = root.
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="1")

    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_activity_parent_name"),
    )

    parent = relationship("Activity", remote_side=[id], back_populates="children")
    # DB policy: on delete parent -> children.parent_id becomes NULL (no ORM cascade delete)
    children = relationship("Activity", back_populates="parent", passive_deletes=True)

    organizations = relationship(
        "Organization",
        secondary="organization_activity",
        back_populates="activities",
    )
