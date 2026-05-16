import os
import secrets
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

# Env file directory
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


def normalize_database_url(url: str) -> str:
    """Make SQLAlchemy Postgres URLs explicit for the psycopg3 driver."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    scheme, sep, rest = url.partition("://")
    if not sep:
        return url
    if "+" not in scheme and scheme == "postgresql":
        scheme = "postgresql+psycopg"
    return f"{scheme}://{rest}"


def get_sqlalchemy_database_uri(instance_path: str) -> str:
    """
    Resolve DB URI for Flask-SQLAlchemy.

    Set DATABASE_URL or SQLALCHEMY_DATABASE_URI to use PostgreSQL (e.g. RDS,
    Aurora, Docker Postgres, etc.). Omit both for default SQLite under the
    Flask instance folder.
    """
    raw = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if raw:
        return normalize_database_url(raw)
    return "sqlite:///" + os.path.join(instance_path, "hidb.sqlite")


def get_secret_key(instance_path: str) -> str:
    """
    Resolve the Flask session signing key.

    Deployments can set SECRET_KEY explicitly. Local/self-hosted installs get a
    generated key stored under the Flask instance folder so old cookies from a
    different install cannot be reused.
    """
    env_secret = os.getenv("SECRET_KEY")
    if env_secret:
        return env_secret

    os.makedirs(instance_path, exist_ok=True)
    secret_path = Path(instance_path) / "secret_key"
    if secret_path.exists():
        return secret_path.read_text(encoding="utf-8").strip()

    generated = secrets.token_urlsafe(32)
    secret_path.write_text(generated, encoding="utf-8")
    secret_path.chmod(0o600)
    return generated


config = SimpleNamespace(
    ENVIRONMENT=os.getenv("ENVIRONMENT", "production"),
    HOST=os.getenv("HOST", "127.0.0.1"),
    PORT=int(os.getenv("PORT", "5000")),
)
