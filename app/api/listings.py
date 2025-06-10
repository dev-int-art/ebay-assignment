from fastapi import APIRouter
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import Select, String, Text, case, cast, func, literal_column, union
from sqlalchemy.dialects.postgresql import ARRAY
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
from app.schemas.response import UpsertListingsResponse

router = APIRouter(prefix="/listings", tags=["listings"])


class PropertyValueLike(BaseModel):
    name: str
    type: str
    value: str


@router.get("/test", response_model=list[dict])
async def test():
    with get_db_session() as session:
        results = session.exec(
            select(Property.property_id, Property.name, Property.type)
        ).all()
        return [
            {
                "property_id": result.property_id,
                "name": result.name,
                "type": result.type,
            }
            for result in results
        ]


@router.get("/", response_model=list[dict])
async def get_listings(filters: ListingGetRequest = ListingGetRequest()):
    """Get all listings with optional filters."""
    PAGE_SIZE = 100

    with get_db_session() as session:
        # Create union of property values for aggregation
        string_props = select(
            StringPropertyValue.listing_id,
            StringPropertyValue.property_id,
            StringPropertyValue.value.label("value"),
            literal_column("'str'").label("type"),
        )

        bool_props = select(
            BooleanPropertyValue.listing_id,
            BooleanPropertyValue.property_id,
            BooleanPropertyValue.value.cast(String).label("value"),
            literal_column("'bool'").label("type"),
        )

        property_values_union = union(string_props, bool_props).subquery()

        # Subquery for aggregated properties
        properties_statement = (
            select(
                property_values_union.c.listing_id,
                func.json_agg(
                    func.json_build_object(
                        "name",
                        Property.name,
                        "type",
                        property_values_union.c.type,
                        "value",
                        property_values_union.c.value,
                    )
                )
                .filter(Property.name.is_not(None))
                .label("properties"),
            )
            .join(Property, Property.property_id == property_values_union.c.property_id)
            .group_by(property_values_union.c.listing_id)
        )

        properties_subquery = (properties_statement).subquery()

        # Subquery for aggregated entities
        entities_statement = (
            select(
                Listing.listing_id,
                func.json_agg(
                    func.json_build_object(
                        "name", DatasetEntity.name, "data", DatasetEntity.data
                    )
                )
                .filter(DatasetEntity.name.is_not(None))
                .label("entities"),
            )
            .join(
                DatasetEntity, Listing.dataset_entity_ids.any(DatasetEntity.entity_id)
            )
            .group_by(Listing.listing_id)
        )
        if filters.dataset_entities:
            # Filter by dataset entities with matching JSON data
            entities_statement = entities_statement.where(
                DatasetEntity.data.op("@>")(filters.dataset_entities)
            )

        entities_subquery = (entities_statement).subquery()

        # Main query with subqueries
        statement = (
            select(
                Listing.listing_id,
                Listing.scan_date,
                Listing.is_active,
                Listing.dataset_entity_ids,
                Listing.image_hashes,
                func.coalesce(
                    properties_subquery.c.properties, func.json_build_array()
                ).label("properties"),
                func.coalesce(
                    entities_subquery.c.entities, func.json_build_array()
                ).label("entities"),
            )
            .join(
                properties_subquery,
                properties_subquery.c.listing_id == Listing.listing_id,
                isouter=True,
            )
            .join(
                entities_subquery,
                entities_subquery.c.listing_id == Listing.listing_id,
                isouter=True,
            )
        )
        if filters.dataset_entities:
            statement = statement.where(
                func.cardinality(Listing.dataset_entity_ids) > 0
            )

        # Filter listings by properties
        if filters.properties:
            # Create conditions for each property filter
            property_condition = None
            for property_id, expected_value in filters.properties.items():
                bool_value = (
                    str(TypeAdapter(bool).validate_python(expected_value)).lower()
                    if is_bool_like(expected_value)
                    else expected_value
                )
                # Use EXISTS subquery to check if listing has the specified property value
                # property_values_union already has property_id and type information
                property_exists = (
                    select(1)
                    .select_from(property_values_union)
                    .where(
                        (property_values_union.c.listing_id == Listing.listing_id)
                        & (property_values_union.c.property_id == int(property_id))
                        & case(
                            (
                                property_values_union.c.type == "bool",
                                property_values_union.c.value == bool_value,
                            ),
                            (
                                property_values_union.c.type == "str",
                                property_values_union.c.value == expected_value,
                            ),
                            else_=False,
                        )
                    )
                ).exists()

                property_condition = (
                    property_exists
                    if property_condition is None
                    else (property_condition & property_exists)
                )

            statement = statement.where(property_condition)

        # Apply filters
        statement = await _add_filters(statement, filters)

        if filters.page:
            statement = statement.offset((filters.page - 1) * PAGE_SIZE)

        statement = statement.order_by(Listing.listing_id).limit(PAGE_SIZE)

        results = session.exec(statement).all()

        # Convert results to the desired structure
        formatted_results = []
        for result in results:
            formatted_result = {
                "listing_id": result.listing_id,
                "scan_date": result.scan_date.isoformat() if result.scan_date else None,
                "is_active": result.is_active,
                "dataset_entity_ids": result.dataset_entity_ids,
                "image_hashes": result.image_hashes,
                "properties": result.properties if result.properties != [None] else [],
                "entities": result.entities if result.entities != [None] else [],
            }
            formatted_results.append(formatted_result)

        return formatted_results


async def _add_filters(statement: Select, filters: ListingGetRequest):
    """Add filters to the query statement."""
    if filters.listing_id:
        statement = statement.where(Listing.listing_id == filters.listing_id)

    if filters.scan_date_from and filters.scan_date_to:
        statement = statement.where(
            Listing.scan_date >= filters.scan_date_from,
            Listing.scan_date <= filters.scan_date_to,
        )

    if filters.is_active is not None:
        statement = statement.where(Listing.is_active == filters.is_active)

    if filters.image_hashes:
        statement = statement.where(
            Listing.image_hashes.overlap(cast(filters.image_hashes, ARRAY(Text)))
        )

    return statement


@router.put("/", response_model=UpsertListingsResponse)
async def upsert_listings(listings_data: UpsertListingsRequest):
    """
    Insert or update multiple listings with their properties and entities.
    `UpsertListingsRequest` is the source of truth.
    """
    with get_db_session() as session:
        listings = listings_data.listings
        current_listing_index = ""

        try:
            for index, listing_data in enumerate(listings):
                current_listing_index = listing_data.listing_id

                listing_obj = await _upsert_listing(listing_data, session)

                # Handle Properties
                await _upsert_properties(
                    properties=listing_data.properties,
                    session=session,
                    listing_id=listing_data.listing_id,
                )

                # Handle Entities
                entity_ids = await _upsert_entities(
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


async def _upsert_listing(listing_data: UpsertListing, session: Session) -> Listing:
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


async def _upsert_properties(
    properties: list[Property], session: Session, listing_id: str
):
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


async def _upsert_entities(
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
