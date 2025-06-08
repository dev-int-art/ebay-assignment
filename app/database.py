from contextlib import contextmanager

from dotenv import dotenv_values
from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    BooleanPropertyValue,
    DatasetEntity,
    Listing,
    Property,
    PropertyType,
    StringPropertyValue,
)

config = dotenv_values(".env")
DATABASE_URL = config.get("DATABASE_URL", "")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)


async def initialize_database():
    """Create the database tables."""
    SQLModel.metadata.create_all(engine)
    print("Database initialized successfully.")


def drop_database():
    """Drop the database tables."""
    SQLModel.metadata.drop_all(engine)
    print("Database dropped successfully.")


@contextmanager
def get_db_session():
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
        raise e
    finally:
        session.close()
        print("Session closed.")
