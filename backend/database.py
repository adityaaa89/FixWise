"""
database.py
===========
SQLAlchemy Database Configuration and Session Management for the
Repair or Replace Advisor backend.

Uses SQLite by default (`sqlite:///./advisor.db`), easily swappable via
the `DATABASE_URL` environment variable.
"""

from __future__ import annotations

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./advisor.db")

# For SQLite, ensure check_same_thread=False for multithreaded ASGI requests
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

