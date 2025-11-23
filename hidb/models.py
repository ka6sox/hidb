from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    
    # Relationships
    rooms: Mapped[List["Room"]] = relationship(back_populates="creator", cascade="all, delete-orphan")
    locations: Mapped[List["Location"]] = relationship(back_populates="creator", cascade="all, delete-orphan")
    items: Mapped[List["Item"]] = relationship(back_populates="creator", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.username}>'


class Room(db.Model):
    __tablename__ = 'rooms'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    creator: Mapped["User"] = relationship(back_populates="rooms")
    items: Mapped[List["Item"]] = relationship(back_populates="room", foreign_keys="Item.room_id")
    
    def __repr__(self):
        return f'<Room {self.description}>'


class Location(db.Model):
    __tablename__ = 'locations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    creator: Mapped["User"] = relationship(back_populates="locations")
    items: Mapped[List["Item"]] = relationship(back_populates="location", foreign_keys="Item.location_id")
    
    def __repr__(self):
        return f'<Location {self.description}>'


class Item(db.Model):
    __tablename__ = 'items'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    serial_no: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    room_id: Mapped[int] = mapped_column('room', Integer, ForeignKey('rooms.id'), nullable=False)
    location_id: Mapped[int] = mapped_column('location', Integer, ForeignKey('locations.id'), nullable=False)
    sublocation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    date_added: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    date_acquired: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    creator: Mapped["User"] = relationship(back_populates="items")
    room: Mapped["Room"] = relationship(back_populates="items", foreign_keys=[room_id])
    location: Mapped["Location"] = relationship(back_populates="items", foreign_keys=[location_id])
    
    def __repr__(self):
        return f'<Item {self.name}>'
