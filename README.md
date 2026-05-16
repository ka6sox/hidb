# HIDB

**Home Inventory DataBase**

How many of us have bought something and put it “someplace” and forgot where you put it only to have to go buy it again? I wanted something simple that would walk me right to where I put the thing I need, so I created the HIDB project.

HIDB is a relational database for keeping track of where you put things in your home using your phone or tablet. The goal of this app is to make it so that you can add items, and describe where you put them so you can find them easily.

You can run HIDB on any computer or even a Pi! You can then access HIDB from your phone, tablet or computer to create, edit, and find where you put things. It runs as a Docker Image so it can be self-contained and easy to deploy. We are looking into a HIDB hosting service for those who would like to use this but would rather not run it locally.



**Note: this README is a work in progress.**

## Setting up for development

**The below steps are only meant for running this code in a development environment.** If you intend
to run this in production, please see "Running in a Production setting" below.

Use [Pyenv](https://github.com/pyenv/pyenv) to manage multiple Python versions.

```shell
# Developed using Python 3.13.2

# Install pyenv (examples):
# - Debian/Ubuntu: apt install pyenv
# - RHEL/CentOS/Fedora: yum install pyenv (or dnf install pyenv)

# Ensure pyenv is initialized for your shell (bash example):
# Add the following to your ~/.bashrc (and/or ~/.profile depending on your system),
# then restart your terminal:
#   export PYENV_ROOT="$HOME/.pyenv"
#   export PATH="$PYENV_ROOT/bin:$PATH"
#   eval "$(pyenv init - bash)"
#
# Verify pyenv is available:
$ pyenv --version

# Install the project's Python version (one-time)
$ pyenv install 3.13.2

# Select the Python version for this repository
$ pyenv local 3.13.2

# Verify your shell is using the selected Python
$ python --version

# Set up a Python virtualenv
$ python -m venv env
$ source env/bin/activate

# Install the app and dev dependencies (tests, coverage)
$ pip install -e ".[dev]"
# Or: pip install -r requirements-dev.txt
```

## Database backend (SQLite or PostgreSQL)

By default the app uses **SQLite** at `<instance>/hidb.sqlite` (the Flask instance folder, usually `instance/` next to the package).

To use **PostgreSQL** (including Amazon RDS or Aurora PostgreSQL), set a URL before running the app or migrations:

```shell
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/DBNAME'
# Optional alias:
# export SQLALCHEMY_DATABASE_URI='postgresql://...'
```

`postgres://` URLs are accepted and normalized. Bare `postgresql://` schemes are wired to the **psycopg** (v3) driver.

Keep using `flask --app hidb db upgrade` (or `docker compose exec web flask db upgrade`) against whichever database the environment points at.

```shell
# Apply database migrations (creates / updates tables; safe for existing data)
$ flask --app hidb db upgrade

# If you already had a SQLite DB from before migrations were added, and the
# schema already matches the app, stamp Alembic once (does not change tables):
# $ flask --app hidb db stamp head

# Destructive reset: drop all tables and re-apply migrations from scratch
# (same as the old init-db behavior — all data is lost)
$ flask --app hidb init-db

# Run the app
# The web app will be accessable at http://localhost:5000/
# Add "-host=0.0.0.0" to allow access from the network; otherwise only localhost is allowed
# This should NOT be used in a production environment!
$ flask --app hidb --debug run

# Run unit tests
$ pytest

# Measure code coverage
$ coverage run -m pytest
$ coverage report
$ coverage html
```

## Database migrations (Flask-Migrate / Alembic)

Step-by-step workflow for editing models and shipping revisions: [HOW_TO_CHANGE_SCHEMA.md](HOW_TO_CHANGE_SCHEMA.md).

Schema changes are tracked under `migrations/versions/`. Typical commands (from the repo root, venv active):

| Command | Purpose |
| --- | --- |
| `flask --app hidb db upgrade` | Apply all pending migrations (use this after `git pull` or on deploy). |
| `flask --app hidb db migrate -m "short message"` | Autogenerate a new revision from your SQLAlchemy models (review the file before committing). |
| `flask --app hidb db downgrade` | Roll back one revision (use with care; SQLite has limits on some operations). |
| `flask --app hidb db stamp head` | Mark the DB as current **without** running migrations (only when the schema already matches `head`). |
| `flask --app hidb init-db` | **Destructive:** `drop_all` + `upgrade` — wipes the database and rebuilds from migrations. |

Docker Compose example after a deploy or image update:

```shell
docker compose exec web flask db upgrade
```

## Running in a Production setting

Use one of the [supported methods of deploying a Flask app](https://flask.palletsprojects.com/en/2.0.x/deploying/).
There are many options available, both commercial/third-party and self-hosted.

```shell
# Install build tooling (once)
$ pip install build

# Build a wheel under dist/
$ python -m build

# Install the wheel in a venv or on a host (runtime deps included)
$ pip install dist/hidb-*.whl
```

This repository also contains the configuration necessary to deploy this app in a [Docker](https://www.docker.com/)
container, which is the usual production path.

```shell
# Build Docker image (re-run after code or dependency changes)
$ docker compose build

# Start container
$ docker compose up

# Apply migrations after deploy or image update
$ docker compose exec web flask db upgrade

# Shut down
$ docker compose down
```
