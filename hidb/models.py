from datetime import datetime
from typing import List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()

item_tags = db.Table(
    "item_tags",
    db.Column(
        "item_id",
        Integer,
        ForeignKey("items.id"),
        primary_key=True,
    ),
    db.Column(
        "tag_id",
        Integer,
        ForeignKey("tags.id"),
        primary_key=True,
    ),
)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "uq_users_single_owner",
            "role",
            unique=True,
            sqlite_where=text("role = 'owner'"),
            postgresql_where=text("role = 'owner'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="reader")
    editor_for_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    role_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    role_updated_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    password_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    places: Mapped[List["Place"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )
    items: Mapped[List["Item"]] = relationship(
        back_populates="creator", cascade="all, delete-orphan"
    )
    editor_for: Mapped[Optional["User"]] = relationship(
        remote_side="User.id",
        foreign_keys=[editor_for_id],
        back_populates="editors",
    )
    editors: Mapped[List["User"]] = relationship(
        foreign_keys=[editor_for_id],
        back_populates="editor_for",
    )
    role_updated_by: Mapped[Optional["User"]] = relationship(
        remote_side="User.id",
        foreign_keys=[role_updated_by_id],
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
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
    sublocation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_added: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    date_acquired: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    creator: Mapped["User"] = relationship(back_populates="items")
    place: Mapped["Place"] = relationship(back_populates="items")
    tags: Mapped[List["Tag"]] = relationship(
        secondary=item_tags,
        back_populates="items",
        order_by="Tag.name",
    )

    def __repr__(self) -> str:
        return f"<Item {self.name}>"


class Tag(db.Model):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    items: Mapped[List["Item"]] = relationship(
        secondary=item_tags,
        back_populates="tags",
        order_by="Item.name",
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"
