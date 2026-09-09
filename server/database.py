"""SQLite database initialization with SQLModel."""

from pathlib import Path
from sqlmodel import SQLModel, create_engine

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create all tables."""
    SQLModel.metadata.create_all(engine)
