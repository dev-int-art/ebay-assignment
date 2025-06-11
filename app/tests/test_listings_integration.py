import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import get_db_session
from app.main import app
from app.models import Property


@pytest.mark.integration
def test_get_listings_endpoint(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get("/listings/")

        assert response.status_code == 200

        data = response.json()
        assert "listings" in data
        assert "total" in data
        assert data["total"] == 3

        listings = data["listings"]
        assert len(listings) == 3

        first_listing = listings[0]
        assert first_listing["listing_id"] == "112"
        assert first_listing["is_active"] is True
        assert "hash1" in first_listing["image_hashes"]
        assert len(first_listing["properties"]) == 2

        bool_property = next(
            prop for prop in first_listing["properties"] if prop["type"] == "bool"
        )
        assert bool_property["name"] == "Has Delivery"
        assert bool_property["value"] is False


@pytest.mark.integration
def test_get_listings_with_listing_id(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get("listings/", params={"listing_id": "112"})

        assert response.status_code == 200

        data = response.json()
        listings = data["listings"]

        assert "listings" in data
        assert "total" in data
        assert data["total"] == len(listings)

        first_listing = listings[0]
        assert first_listing["listing_id"] == "112"


@pytest.mark.integration
def test_get_listings_with_from_to_dates(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get(
            "listings/",
            params={"scan_date_from": "2020-06-10", "scan_date_to": "2025-01-01"},
        )

        assert response.status_code == 200

        data = response.json()
        listings = data["listings"]

        assert data["total"] == 0
        assert len(listings) == 0


@pytest.mark.integration
def test_get_listings_with_from_date(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get("listings/", params={"scan_date_from": "2020-06-10"})

        assert response.status_code == 200

        data = response.json()
        listings = data["listings"]

        assert data["total"] == 3
        assert len(listings) == 3


@pytest.mark.integration
def test_get_listings_with_image_hashes(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get("listings/", params={"image_hashes": ["hash1", "hash2"]})

        assert response.status_code == 200

        data = response.json()
        listings = data["listings"]

        assert data["total"] == 2
        assert len(listings) == 2


@pytest.mark.integration
def test_get_listings_with_dataset_entities(
    create_sample_listings, cleanup_test_database
):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        response = client.get('listings/?dataset_entities={"key1": "value1"}')

        assert response.status_code == 200
        data = response.json()
        listings = data["listings"]

        assert data["total"] == 2
        assert len(listings) == 2

        response = client.get('listings/?dataset_entities={"key3": "value3"}')

        data = response.json()
        listings = data["listings"]

        assert data["total"] == 1
        assert len(listings) == 1


@pytest.mark.integration
def test_get_listings_with_properties(create_sample_listings, cleanup_test_database):
    """Integration test for GET /listings endpoint."""
    with TestClient(app) as client:
        property_id = 1
        with get_db_session() as session:
            property_id = session.exec(
                select(Property.property_id).where(Property.name == "Has Delivery")
            ).first()

        response = client.get(
            f"listings/?properties={json.dumps({property_id: 'false'})}"
        )

        assert response.status_code == 200
        data = response.json()
        listings = data["listings"]

        assert data["total"] == 1
        assert len(listings) == 1


@pytest.mark.integration
def test_get_listings_empty_response():
    with TestClient(app) as client:
        response = client.get("/listings/")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["listings"]) == 0
