"""Schema Pydantic (request/response) modul drivers."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.core.constants import DriverApplicationStatus, OrderStatus, ServiceRequestType
from app.core.response import Meta, SuccessResponse


class DriverApplicationCreate(BaseModel):
    application_note: str | None = None


class DriverApplicationUser(BaseModel):
    id: int
    name: str


class DriverApplicationRead(BaseModel):
    id: int
    status: DriverApplicationStatus
    application_note: str | None
    reviewed_at: datetime | None
    created_at: datetime
    user: DriverApplicationUser


class DriverApplicationResponse(SuccessResponse[DriverApplicationRead]):
    pass


class DriverOrderUser(BaseModel):
    id: int
    name: str


class DriverOrderLocation(BaseModel):
    id: int
    name: str
    category: str
    latitude: float | None
    longitude: float | None


class DriverOrderServiceType(BaseModel):
    id: int
    name: str
    code: str


class DriverOrderRead(BaseModel):
    id: int
    status: OrderStatus
    service_type: DriverOrderServiceType
    customer: DriverOrderUser
    driver: DriverOrderUser | None
    pickup_location: DriverOrderLocation | None
    destination_location: DriverOrderLocation | None
    service_request_type: ServiceRequestType | None
    item_description: str | None
    passenger_count: int | None
    optional_cost_expectation: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DriverOrderHistoryResponse(SuccessResponse[list[DriverOrderRead]]):
    meta: Meta
