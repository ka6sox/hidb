DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS items;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

/*
 * Location:
 *    Room of house [Dropdown Menu + Custom]
 *    Area in room (cabinet x, etc.)
 *    Sub-location within area(box y, Drawer Z18, etc.)
 *
 * Photo(s)
 */

CREATE TABLE items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_id INTEGER NOT NULL,
  description TEXT NOT NULL,
  model_no TEXT NOT NULL,
  qty INTEGER NOT NULL,
  cost REAL NOT NULL,
  date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  date_acquired TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (creator_id) REFERENCES user (id)
);
