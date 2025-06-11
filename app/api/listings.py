import logging

from fastapi import APIRouter
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import Select, and_, func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.api.utils import is_bool_like
from app.database import get_db_session
from app.models import (
    BooleanPropertyValue,
    DatasetEntity,
    Listing,
    Property,
    PropertyType,
    StringPropertyValue,
)
from app.schemas.request import (
    Entity,
    ListingGetRequest,
    UpsertListing,
    UpsertListingsRequest,
)
from app.schemas.response import ListingGet, ListingsGetResponse, UpsertListingsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/listings", tags=["listings"])


class PropertyValueLike(BaseModel):
    name: str
    type: str
    value: str


@router.get("/", response_model=ListingsGetResponse)
def get_listings(filters: ListingGetRequest = ListingGetRequest()):
    """Get all listings with optional filters."""
    logger.info(f"GET /listings/ - Filters: {filters}")
    PAGE_SIZE = 100

    with get_db_session() as session:
        statement = (
            select(
                Listing,
                func.coalesce(
                    func.json_agg(
                        func.json_build_object(
                            "name", DatasetEntity.name, "data", DatasetEntity.data
                        )
                    ),
                    func.json_build_array(),
                ).label("entities"),
            )
            .options(
                selectinload(Listing.string_property_values).selectinload(
                    StringPropertyValue.property
                ),
                selectinload(Listing.boolean_property_values).selectinload(
                    BooleanPropertyValue.property
                ),
            )
            .join(
                DatasetEntity, Listing.dataset_entity_ids.any(DatasetEntity.entity_id)
            )
            .filter(DatasetEntity.name.is_not(None))
            .group_by(Listing.listing_id)
        )

        if filters.dataset_entities:
            statement = statement.where(
                and_(
                    func.cardinality(Listing.dataset_entity_ids) > 0,
                    DatasetEntity.data.op("@>")(filters.dataset_entities),
                )
            )

        property_filters = _get_property_filters(filters.properties, session)
        statement = _add_property_filters(statement, property_filters)

        statement = _add_filters(statement, filters)

        count_statement = select(func.count(Listing.listing_id.distinct())).select_from(
            statement.subquery()
        )
        total_count = session.exec(count_statement).one()

        if filters.page:
            statement = statement.offset((filters.page - 1) * PAGE_SIZE)

        statement = statement.order_by(Listing.listing_id).limit(PAGE_SIZE)
        results = session.exec(statement).all()

        formatted_results = _get_formatted_results(results)

        return ListingsGetResponse(
            listings=formatted_results,
            total=total_count,
        )


def _add_property_filters(statement: Select, property_filters: list) -> Select:
    """Add property filters to the query statement."""
    if property_filters:
        combined_filter = property_filters[0]
        for filter_condition in property_filters[1:]:
            combined_filter = combined_filter & filter_condition
        statement = statement.where(combined_filter)
    return statement


def _get_property_filters(properties: dict[int, str], session: Session) -> list[Select]:
    properties_where_clause = []

    if not properties:
        return properties_where_clause

    for property_id, expected_value in properties.items():
        property_type = session.exec(
            select(Property.type).where(Property.property_id == property_id)
        ).first()

        # TODO: Create a map that stores "string": {table: StringPropertyValue, formatter: lambda} (for scope creep)
        if property_type == PropertyType.BOOLEAN:
            bool_value = (
                TypeAdapter(bool).validate_python(expected_value)
                if is_bool_like(expected_value)
                else expected_value
            )
            subquery = (
                select(1).where(
                    BooleanPropertyValue.property_id == property_id,
                    BooleanPropertyValue.value == bool_value,
                    BooleanPropertyValue.listing_id == Listing.listing_id,
                )
            ).exists()
            properties_where_clause.append(subquery)
        elif property_type == PropertyType.STRING:
            subquery = (
                select(1).where(
                    StringPropertyValue.property_id == property_id,
                    StringPropertyValue.value == expected_value,
                    StringPropertyValue.listing_id == Listing.listing_id,
                )
            ).exists()
            properties_where_clause.append(subquery)

    return properties_where_clause


def _add_filters(statement: Select, filters: ListingGetRequest):
    """Add filters to the query statement."""
    if filters.listing_id:
        statement = statement.where(Listing.listing_id == filters.listing_id)

    if filters.scan_date_from:
        statement = statement.where(Listing.scan_date >= filters.scan_date_from)

    if filters.scan_date_to:
        statement = statement.where(Listing.scan_date <= filters.scan_date_to)

    if filters.is_active is not None:
        statement = statement.where(Listing.is_active == filters.is_active)

    if filters.image_hashes:
        statement = statement.where(Listing.image_hashes.op("&&")(filters.image_hashes))

    return statement


def _get_formatted_results(
    results: list[tuple[Listing, list[dict]]],
) -> list[ListingGet]:
    formatted_results = []
    for result in results:
        listing, entities = result
        str_properties = listing.string_property_values
        bool_properties = listing.boolean_property_values

        properties = []
        for property in str_properties + bool_properties:
            properties.append(
                {
                    "name": property.property.name,
                    "type": property.property.type,
                    "value": property.value,
                }
            )

        formatted_results.append(
            ListingGet(
                listing_id=listing.listing_id,
                scan_date=listing.scan_date.isoformat(sep=" ")
                if listing.scan_date
                else "",
                is_active=listing.is_active,
                image_hashes=listing.image_hashes,
                properties=properties,
                entities=entities,
            )
        )

    return formatted_results


@router.put("/", response_model=UpsertListingsResponse)
def upsert_listings(listings_data: UpsertListingsRequest):
    """
    Insert or update multiple listings with their properties and entities.
    `UpsertListingsRequest` is the source of truth.
    """
    logger.info(f"PUT /listings/ - Upserting {len(listings_data.listings)} listings")

    with get_db_session() as session:
        listings = listings_data.listings
        current_listing_index = ""

        try:
            for index, listing_data in enumerate(listings):
                current_listing_index = listing_data.listing_id

                listing_obj = _upsert_listing(listing_data, session)

                _upsert_properties(
                    properties=listing_data.properties,
                    session=session,
                    listing_id=listing_data.listing_id,
                )

                entity_ids = _upsert_entities(
                    entities=listing_data.entities,
                    session=session,
                    listing_id=listing_data.listing_id,
                )

                # Update listing with entity IDs
                listing_obj.dataset_entity_ids = entity_ids
                return UpsertListingsResponse(status="success", error=None)
        except Exception as e:
            session.rollback()
            return UpsertListingsResponse(
                status="failed",
                error={"listing_id": current_listing_index, "error": str(e)},
            )


def _upsert_listing(listing_data: UpsertListing, session: Session) -> Listing:
    existing_listing = session.exec(
        select(Listing).where(Listing.listing_id == listing_data.listing_id)
    ).first()

    if existing_listing:
        # Update existing listing
        existing_listing.scan_date = listing_data.scan_date
        existing_listing.is_active = listing_data.is_active
        existing_listing.image_hashes = listing_data.image_hashes
        existing_listing.dataset_entity_ids = []  # Will be populated from entities
        session.add(existing_listing)

        listing_obj = existing_listing
    else:
        # Create new listing
        new_listing = Listing(
            listing_id=listing_data.listing_id,
            scan_date=listing_data.scan_date,
            is_active=listing_data.is_active,
            image_hashes=listing_data.image_hashes,
            dataset_entity_ids=[],
        )
        session.add(new_listing)
        listing_obj = new_listing

    return listing_obj


def _upsert_properties(properties: list[Property], session: Session, listing_id: str):
    """Upsert properties for a listing."""
    property_table_map = {
        "str": StringPropertyValue,
        "string": StringPropertyValue,
        "bool": BooleanPropertyValue,
        "boolean": BooleanPropertyValue,
    }

    formatter = {
        StringPropertyValue: lambda x: x.value,
        BooleanPropertyValue: lambda x: x.value.lower() == "true",
    }

    for property_data in properties:
        # Find or create Property record
        property_type = property_data.type.lower()
        property_record = session.exec(
            select(Property).where(Property.name == property_data.name)
        ).first()

        if not property_record:
            is_str_property = property_type in ["str", "string"]
            property_record = Property(
                name=property_data.name,
                type=PropertyType.STRING if is_str_property else PropertyType.BOOLEAN,
            )
            session.add(property_record)
            session.flush()  # Get the property_id

        # Property Table. Eg. StringPropertyValue / BooleanPropertyValue
        VALUE_TABLE: type[PropertyValueLike] = property_table_map[property_type]

        existing_value = session.exec(
            select(VALUE_TABLE).where(
                VALUE_TABLE.listing_id == listing_id,
                VALUE_TABLE.property_id == property_record.property_id,
            )
        ).first()

        # Format the value to the correct type
        value = formatter[VALUE_TABLE](property_data)

        # Upsert the value
        if existing_value:
            existing_value.value = value
            session.add(existing_value)
        else:
            property_value = VALUE_TABLE(
                listing_id=listing_id,
                property_id=property_record.property_id,
                value=value,
            )
            session.add(property_value)


def _upsert_entities(
    entities: list[Entity], session: Session, listing_id: str
) -> list[int]:
    entity_ids = []

    for entity_data in entities:
        # Find or create DatasetEntity
        entity_record = session.exec(
            select(DatasetEntity).where(DatasetEntity.name == entity_data.name)
        ).first()

        if not entity_record:
            entity_record = DatasetEntity(name=entity_data.name, data=entity_data.data)
            session.add(entity_record)
            session.flush()  # Get the entity_id
        else:
            # Update existing entity data
            entity_record.data = entity_data.data
            session.add(entity_record)

        entity_ids.append(entity_record.entity_id)

    return entity_ids
