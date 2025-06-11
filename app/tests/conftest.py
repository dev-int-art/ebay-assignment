import logging
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlmodel import SQLModel

from app.database import get_db_session
from app.schemas.request import Entity, Property, UpsertListing, UpsertListingsRequest

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def cleanup_test_database():
    """Cleanup test database after each test."""
    yield

    try:
        with get_db_session() as session:
            for table in reversed(list(SQLModel.metadata.tables.values())):
                session.exec(text(f"TRUNCATE TABLE {table.name} CASCADE"))
            session.commit()
    except Exception as e:
        logger.error(f"Failed to cleanup test database: {e}")
        session.rollback()


@pytest.fixture
def create_sample_listings():
    """Provide sample listings for testing."""
    from app.api.listings import upsert_listings

    listings = UpsertListingsRequest(
        listings=[
            UpsertListing(
                listing_id="112",
                scan_date=datetime.now(),
                is_active=True,
                image_hashes=["hash1"],
                properties=[
                    Property(name="Brand", type="str", value="Samsung"),
                    Property(name="Has Delivery", type="bool", value="false"),
                ],
                entities=[
                    Entity(
                        name="entity_one",
                        data={
                            "key1": "value1",
                            "key2": "value2",
                        },
                    )
                ],
            ),
            UpsertListing(
                listing_id="113",
                scan_date=datetime.now(),
                is_active=True,
                image_hashes=["hash2", "hash3"],
                properties=[
                    Property(name="Brand", type="str", value="Apple"),
                    Property(name="Has Delivery", type="bool", value="true"),
                ],
                entities=[
                    Entity(
                        name="entity_two",
                        data={
                            "key3": "value3",
                        },
                    )
                ],
            ),
            UpsertListing(
                listing_id="114",
                scan_date=datetime.now(),
                is_active=True,
                image_hashes=["hash4", "hash5", "hash6"],
                properties=[
                    Property(name="Brand", type="str", value="Google"),
                    Property(name="Has Delivery", type="bool", value="true"),
                ],
                entities=[
                    Entity(
                        name="entity_one",
                        data={
                            "key1": "value1",
                            "key2": "value2",
                        },
                    )
                ],
            ),
        ],
    )

    response = upsert_listings(listings)
    if response.status == "failed":
        raise Exception(f"Failed to create sample listings: {response.error}")

    return listings
