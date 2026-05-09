import os
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv

# Env file directory
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

config = SimpleNamespace(
    ENVIRONMENT=os.getenv("ENVIRONMENT", "production"),
    HOST=os.getenv("HOST", "127.0.0.1"),
    PORT=int(os.getenv("PORT", "5000")),
)
