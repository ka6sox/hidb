DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS items;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE rooms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_id INTEGER NOT NULL,
  description TEXT NOT NULL,
  FOREIGN KEY (creator_id) REFERENCES users (id)
);

CREATE TABLE locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_id INTEGER NOT NULL,
  description TEXT NOT NULL,
  FOREIGN KEY (creator_id) REFERENCES users (id)
);

CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  serial_no TEXT,
  description TEXT,
  qty INTEGER NOT NULL,
  cost REAL NOT NULL,
  room INTEGER NOT NULL,
  location INTEGER NOT NULL,
  sublocation TEXT,
  photo TEXT,
  date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  date_acquired TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (creator_id) REFERENCES users (id),
  FOREIGN KEY (room) REFERENCES rooms (id)
  FOREIGN KEY (location) REFERENCES locations (id)
);

INSERT INTO users (username, password) VALUES ('admin', 'admin');

INSERT INTO rooms (creator_id, description) VALUES (1, 'Bedroom');
INSERT INTO rooms (creator_id, description) VALUES (1, 'Office');
INSERT INTO rooms (creator_id, description) VALUES (1, 'Living Room');

INSERT INTO locations (creator_id, description) VALUES (1, 'Shelf');
INSERT INTO locations (creator_id, description) VALUES (1, 'Drawer');
INSERT INTO locations (creator_id, description) VALUES (1, 'Cabinet');