from datetime import datetime
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)

    places: Mapped[List["Place"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )
    items: Mapped[List["Item"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Place(db.Model):
    __tablename__ = "places"
    __table_args__ = (
        UniqueConstraint(
            "creator_id",
            "parent_id",
            "name",
            name="uq_place_name_under_parent",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("places.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    creator: Mapped["User"] = relationship(back_populates="places")
    parent: Mapped[Optional["Place"]] = relationship(
        remote_side="Place.id",
        back_populates="children",
    )
    children: Mapped[List["Place"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    items: Mapped[List["Item"]] = relationship(back_populates="place")

    def __repr__(self) -> str:
        return f"<Place {self.name!r}>"


class Item(db.Model):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    place_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("places.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    serial_no: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_added: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    date_acquired: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    creator: Mapped["User"] = relationship(back_populates="items")
    place: Mapped["Place"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<Item {self.name}>"
