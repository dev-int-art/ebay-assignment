import logging
import os
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    BooleanPropertyValue,
    DatasetEntity,
    Listing,
    Property,
    PropertyType,
    StringPropertyValue,
)

# Configure logging
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)


class DatabaseError(Exception):
    """Custom exception for database operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


async def initialize_database(use_engine: Engine | None = None):
    """Create the database tables."""
    try:
        SQLModel.metadata.create_all(use_engine or engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError("Failed to initialize database", original_error=e)


async def drop_database(use_engine: Engine | None = None):
    """Drop the database tables."""
    SQLModel.metadata.drop_all(use_engine or engine)
    logger.info("Database dropped successfully.")


@contextmanager
def get_db_session(use_engine: Engine | None = None):
    session = Session(use_engine or engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database operation failed: {e}")
        # Raise a concealed database error
        raise DatabaseError("Database operation failed", original_error=e)
    finally:
        session.close()
