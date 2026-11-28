"""Schema Pydantic (request/response) modul orders."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.constants import OrderStatus, ServiceRequestType
from app.core.response import Meta, SuccessResponse


class OrderCreate(BaseModel):
    service_type: Literal["ANTAR_JEMPUT", "JASA_TITIP"]
    pickup_location_id: int = Field(gt=0)
    destination_location_id: int = Field(gt=0)
    description: str = Field(min_length=1)
    expected_cost: Decimal | None = Field(
        default=None,
        ge=0,
        le=Decimal("9999999999.99"),
        max_digits=12,
        decimal_places=2,
    )

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Deskripsi wajib diisi.")
        return value


class OrderStatusUpdate(BaseModel):
    status: Literal["ON_THE_WAY", "COMPLETED"]


class OrderUserRead(BaseModel):
    id: int
    name: str


class OrderLocationRead(BaseModel):
    id: int
    name: str
    category: str
    latitude: float | None
    longitude: float | None


class OrderServiceTypeRead(BaseModel):
    id: int
    name: str
    code: str


class OrderRead(BaseModel):
    id: int
    status: OrderStatus
    service_type: OrderServiceTypeRead
    customer: OrderUserRead
    driver: OrderUserRead | None
    pickup_location: OrderLocationRead | None
    destination_location: OrderLocationRead | None
    service_request_type: ServiceRequestType | None
    item_description: str | None
    passenger_count: int | None
    optional_cost_expectation: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class OrderAcceptResponse(SuccessResponse[OrderRead]):
    pass


class OrderListResponse(SuccessResponse[list[OrderRead]]):
    meta: Meta
