import enum
from datetime import datetime
from typing import Dict, List

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Column, Enum, Field, SQLModel


class Listing(SQLModel, table=True):
    __tablename__ = "test_listings"

    listing_id: str = Field(default=None, primary_key=True)
    scan_date: datetime
    is_active: bool = Field(default=True)
    dataset_entity_ids: List[int] = Field(sa_column=Column(ARRAY(Integer)))
    image_hashes: List[str] = Field(sa_column=Column(ARRAY(Integer)))

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S"),
        }


class PropertyType(enum.Enum):
    STRING = "string"
    BOOLEAN = "boolean"


class Property(SQLModel, table=True):
    __tablename__ = "test_properties"

    property_id: int = Field(default=None, primary_key=True)
    name: str
    type: PropertyType = Field(
        sa_column=Column(
            Enum(PropertyType),
            nullable=False,
        ),
    )


class StringPropertyValue(SQLModel, table=True):
    __tablename__ = "test_property_values_str"

    listing_id: str = Field(
        foreign_key="test_listings.listing_id", primary_key=True, index=True
    )
    property_id: int = Field(
        foreign_key="test_properties.property_id", primary_key=True, index=True
    )
    value: str


class BooleanPropertyValue(SQLModel, table=True):
    __tablename__ = "test_property_values_bool"

    listing_id: str = Field(
        foreign_key="test_listings.listing_id", primary_key=True, index=True
    )
    property_id: int = Field(
        foreign_key="test_properties.property_id", primary_key=True, index=True
    )
    value: bool


class DatasetEntity(SQLModel, table=True):
    __tablename__ = "test_dataset_entities"

    entity_id: int = Field(nullable=False, primary_key=True)
    name: str = Field(nullable=False, unique=True)
    data: Dict = Field(
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )
