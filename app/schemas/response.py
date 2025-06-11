from typing import Union

from pydantic import BaseModel


class UpsertListingsError(BaseModel):
    listing_id: str
    error: str


class UpsertListingsResponse(BaseModel):
    status: str
    error: UpsertListingsError | None


class ListingGetProperty(BaseModel):
    name: str
    type: str
    value: Union[str, bool]  # Can be either string or boolean


class ListingGetEntity(BaseModel):
    name: str
    data: dict


class ListingGet(BaseModel):
    listing_id: str
    scan_date: str
    is_active: bool
    image_hashes: list[str]
    properties: list[ListingGetProperty]
    entities: list[ListingGetEntity]


class ListingsGetResponse(BaseModel):
    listings: list[ListingGet]
    total: int
