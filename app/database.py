import logging
import os
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.models import (  # noqa: F401
    BooleanPropertyValue,
    DatasetEntity,
    Listing,
    Property,
    PropertyType,
    StringPropertyValue,
)

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


def get_engine() -> Engine:
    DATABASE_URL = os.environ["DATABASE_URL"]

    if os.environ.get("PYTEST_VERSION"):
        DATABASE_URL = os.environ.get(
            "TEST_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/test_listings_db",
        )

    return create_engine(
        DATABASE_URL,
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
    )


async def initialize_database():
    """Create the database tables."""
    try:
        engine = get_engine()
        SQLModel.metadata.create_all(engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError("Failed to initialize database", original_error=e)


def drop_database():
    """Drop the database tables."""
    engine = get_engine()
    SQLModel.metadata.drop_all(engine)
    logger.info("Database dropped successfully.")


@contextmanager
def get_db_session():
    engine = get_engine()
    session = Session(engine)
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
