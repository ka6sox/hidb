# How to change the database schema

hidb uses **SQLAlchemy** models and **Flask-Migrate** (Alembic) for schema changes. Revisions live in `migrations/versions/`.

## 1. Edit the models

Change `hidb/models.py`: new tables, columns, types, indexes, constraints, or relationships as needed.

## 2. Generate a migration

From the repository root, with your virtual environment activated:

```shell
flask --app hidb db migrate -m "short description of the change"
```

This creates a new file under `migrations/versions/`. The message should be enough for someone reading git history to understand the change.

## 3. Review the generated revision

Autogenerate is helpful but not infallible. Open the new migration file and check `upgrade()` and `downgrade()`:

- Column renames are often emitted as **drop + add** (data loss) unless you hand-edit.
- **SQLite** has limited `ALTER` support; some operations need Alembic’s batch mode or a custom multi-step migration.

Fix the script before committing if anything looks wrong.

## 4. Apply the migration

```shell
flask --app hidb db upgrade
```

Run the app and tests against the updated database.

## 5. Commit

Commit **both** the model changes and the new file under `migrations/versions/` in the same change (or a tight series of commits) so others can run `db upgrade` after pulling.

---

## Other useful commands

| Situation | Command |
| --- | --- |
| Roll back the last applied migration | `flask --app hidb db downgrade` |
| Database was created before Alembic, and tables already match `head` | `flask --app hidb db stamp head` (once; does not alter tables) |
| Wipe all data and rebuild from migrations | `flask --app hidb init-db` (**destructive**) |
| Deploy / Docker after pulling new migrations | `flask --app hidb db upgrade` or `docker compose exec web flask db upgrade` |

---

## Quick reference

| Step | Action |
| --- | --- |
| 1 | Edit `hidb/models.py` |
| 2 | `flask --app hidb db migrate -m "…"` |
| 3 | Review and fix `migrations/versions/<new_file>.py` |
| 4 | `flask --app hidb db upgrade` |
| 5 | Commit models + migration |

For more context on the ORM migration history, see [archive/MIGRATION_GUIDE.md](archive/MIGRATION_GUIDE.md). For command summaries, see [README.md](README.md#database-migrations-flask-migrate--alembic).
