# Development path: storage and database

This document captures the intended direction for making **photo storage** and **database backends** pluggable. It is planning guidance, not an implementation spec.

## Photo storage (local files vs object storage)

**Today:** uploads go to a directory under the app (`UPLOAD_FOLDER`), filenames are stored in SQLite, and templates link to static URLs under `/static/photos/`.

**Direction:**

- Introduce a small **storage abstraction** used by item create/update/delete: save uploaded bytes, delete by key, and produce a **display URL** for templates.
- Provide two backends: **local filesystem** (current behavior) and **S3-compatible object storage** (e.g. AWS S3), chosen via configuration.
- Keep storing a **stable object key** (or filename) in the database; avoid baking “local vs cloud” into the schema beyond that key.
- **Serving:** local keeps using Flask static routes; cloud typically uses a **public base URL** (or CDN in front of the bucket) or **presigned URLs** if objects stay private.

**Why:** one codebase can run on a laptop with disk storage or in production with durable, scalable object storage without rewriting views around upload mechanics.

## Database (SQLite vs PostgreSQL and managed Postgres)

**Today:** the app uses **SQLAlchemy** with a configurable **`DATABASE_URL`** (or `SQLALCHEMY_DATABASE_URI`). With no URL set, it defaults to **SQLite** under the Flask instance path; with a URL set, it targets **PostgreSQL** via the **psycopg** driver (including normalized `postgres://` URLs). Engine options differ slightly for SQLite vs server-backed databases (e.g. connection pooling behavior for Postgres).

**Direction:**

- Treat **any SQLAlchemy-supported database** as “set the URL and run migrations,” not as custom app logic.
- **Amazon RDS** and **Aurora PostgreSQL** remain standard Postgres from the application’s perspective; differences are operational (host, TLS, credentials, networking).
- Future niceties (IAM database authentication, rotating secrets) belong next to **how the URL or password is obtained**, not inside models or routes.

**Why:** migrations and models stay portable; deployments swap env vars and infrastructure without forking the app.

## How this fits together

Both efforts follow the same idea: **isolate environment-specific choices behind narrow interfaces or configuration**, keep the **domain model** (what you store in the DB) stable, and let **deployments** choose disk vs S3 and SQLite vs Postgres by configuration.
