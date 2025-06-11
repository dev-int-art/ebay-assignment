from datetime import datetime

from pydantic import BaseModel


class Property(BaseModel):
    name: str
    type: str
    value: str


class Entity(BaseModel):
    name: str
    data: dict


class UpsertListing(BaseModel):
    listing_id: str
    scan_date: datetime
    is_active: bool
    image_hashes: list[str]
    properties: list[Property]
    entities: list[Entity]


class UpsertListingsRequest(BaseModel):
    listings: list[UpsertListing]


class ListingGetRequest(BaseModel):
    page: int | None = 1
    listing_id: str | None = None
    scan_date_from: datetime | None = None
    scan_date_to: datetime | None = None
    is_active: bool | None = None
    image_hashes: list[str] | None = None
    dataset_entities: str | None = None
    properties: str | None = None
