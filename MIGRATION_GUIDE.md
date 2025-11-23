# SQLAlchemy Migration Guide

This document explains the conversion from raw SQL to SQLAlchemy ORM that has been applied to the hidb application.

## Summary of Changes

The application has been fully converted from using raw SQLite queries to using Flask-SQLAlchemy with ORM models. This provides several benefits:

1. **Type Safety**: Models are defined with proper types and relationships
2. **Security**: Eliminates SQL injection vulnerabilities (especially in search.py)
3. **Maintainability**: Easier to understand and modify database operations
4. **Relationships**: Proper object relationships between User, Room, Location, and Item

## Files Changed

### New Files
- `hidb/models.py` - Contains all SQLAlchemy ORM model definitions

### Modified Files
- `requirements.txt` - Added Flask-SQLAlchemy==3.0.2
- `hidb/__init__.py` - Changed from DATABASE to SQLALCHEMY_DATABASE_URI
- `hidb/db.py` - Complete rewrite to use SQLAlchemy
- `hidb/auth.py` - Converted to use User model
- `hidb/rooms.py` - Converted to use Room model
- `hidb/locations.py` - Converted to use Location model
- `hidb/items.py` - Converted to use Item model
- `hidb/search.py` - Converted to use ORM queries (fixes SQL injection)

## Model Definitions

### User Model
```python
class User(db.Model):
    id: Mapped[int]
    username: Mapped[str]
    password: Mapped[str]
    # Relationships: rooms, locations, items
```

### Room Model
```python
class Room(db.Model):
    id: Mapped[int]
    creator_id: Mapped[int]
    description: Mapped[str]
    # Relationships: creator, items
```

### Location Model
```python
class Location(db.Model):
    id: Mapped[int]
    creator_id: Mapped[int]
    description: Mapped[str]
    # Relationships: creator, items
```

### Item Model
```python
class Item(db.Model):
    id: Mapped[int]
    creator_id: Mapped[int]
    name: Mapped[str]
    serial_no: Mapped[Optional[str]]
    description: Mapped[Optional[str]]
    qty: Mapped[int]
    cost: Mapped[Optional[float]]
    room_id: Mapped[int]  # Note: column name is 'room'
    location_id: Mapped[int]  # Note: column name is 'location'
    sublocation: Mapped[Optional[str]]
    photo: Mapped[Optional[str]]
    date_added: Mapped[datetime]
    date_acquired: Mapped[datetime]
    # Relationships: creator, room, location
```

## Database Setup

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Initialize Database

The database initialization command remains the same:

```bash
flask --app hidb init-db
```

This will now use SQLAlchemy's `create_all()` method instead of executing `schema.sql`.

### Migrating Existing Data

If you have an existing SQLite database, it should work without changes as the table schema remains identical. The column names and types are preserved.

**Important**: The existing `schema.sql` file is no longer used by the init-db command, but is kept for reference.

## Key Changes by Module

### auth.py
- `db.execute()` → `User.query.filter_by()` and `User.query.get()`
- `db.commit()` → `db.session.commit()`
- Direct model instantiation for new users
- g.user is now a User object (not a Row)

### rooms.py & locations.py
- Raw SQL queries → SQLAlchemy queries with joins
- Added `func.count()` for item counts
- Results converted to dicts for template compatibility
- Update operations now modify model attributes directly

### items.py
- Complex SQL joins → SQLAlchemy query with `.join()`
- INSERT statements → model instantiation
- UPDATE statements → attribute modification
- DELETE statements → `db.session.delete()`
- `get_item()` returns dict for backward compatibility

### search.py
- **CRITICAL FIX**: Removed SQL injection vulnerability
- String formatting in SQL → Proper parameterized queries
- Raw SQL → SQLAlchemy filter chains
- Much safer and more maintainable code

## Usage Patterns

### Creating Records
```python
# Old way
db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
db.commit()

# New way
user = User(username=username, password=password)
db.session.add(user)
db.session.commit()
```

### Querying Records
```python
# Old way
user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

# New way
user = User.query.filter_by(username=username).first()
```

### Updating Records
```python
# Old way
db.execute("UPDATE rooms SET description = ? WHERE id = ?", (description, id))
db.commit()

# New way
room = Room.query.get(id)
room.description = description
db.session.commit()
```

### Deleting Records
```python
# Old way
db.execute("DELETE FROM rooms WHERE id = ?", (id,))
db.commit()

# New way
room = Room.query.get(id)
db.session.delete(room)
db.session.commit()
```

### Complex Queries with Joins
```python
# Old way
items = db.execute(
    'SELECT i.id, name, '
    '(SELECT description FROM rooms r WHERE room = r.id) as room '
    'FROM items i'
).fetchall()

# New way
items = db.session.query(
    Item.id,
    Item.name,
    Room.description.label('room')
).join(Room, Item.room_id == Room.id).all()
```

## Backward Compatibility

To maintain backward compatibility with existing templates:
- Helper functions (`get_items()`, `get_rooms()`, etc.) return dicts instead of model objects
- Dict keys match the original column names
- Templates don't need to be modified

## Testing

After migration, thoroughly test:
1. User registration and login
2. Creating/updating/deleting rooms and locations
3. Creating/updating/deleting items
4. Search functionality with various criteria
5. Photo uploads and deletions

## Rollback

If you need to rollback, the original raw SQL version can be restored from git history. The database file itself is compatible with both versions.

## Future Improvements

Now that SQLAlchemy is in place, consider:
1. Using Flask-Migrate for database migrations
2. Adding more validation at the model level
3. Implementing proper many-to-many relationships if needed
4. Adding database indexes for performance
5. Using SQLAlchemy events for automatic timestamps
