from pydantic import BaseModel


class UpsertListingsError(BaseModel):
    listing_id: str
    error: str


class UpsertListingsResponse(BaseModel):
    status: str
    error: UpsertListingsError | None
