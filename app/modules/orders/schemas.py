"""Schema Pydantic (request/response) modul orders."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.constants import OrderStatus, ServiceRequestType
from app.core.response import Meta, SuccessResponse


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
