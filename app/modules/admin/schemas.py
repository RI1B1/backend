"""Schema Pydantic modul admin — Master API Reference v1.3."""

from typing import Literal
from pydantic import BaseModel, Field


class AdminOrderItem(BaseModel):
    id: int
    customer_id: int
    driver_id: int | None = None
    service_type: str
    status: str


class AdminOrderListResponse(BaseModel):
    orders: list[AdminOrderItem]


class AdminSummaryDetail(BaseModel):
    total_orders: int
    open_orders: int
    accepted_orders: int
    on_the_way_orders: int
    completed_orders: int
    cancelled_orders: int
    active_drivers: int
    pending_driver_applications: int


class AdminSummaryResponse(BaseModel):
    summary: AdminSummaryDetail


class AdminDriverApplicationItem(BaseModel):
    id: int
    user_id: int
    vehicle_type: str
    vehicle_description: str | None = None
    status: str


class AdminDriverApplicationListResponse(BaseModel):
    applications: list[AdminDriverApplicationItem]


class DriverApplicationReviewRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED"]


class DriverApplicationReviewItem(BaseModel):
    id: int
    status: str


class DriverApplicationReviewResponse(BaseModel):
    message: str
    application: DriverApplicationReviewItem


class AdminLocationItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_active: bool


class AdminLocationListResponse(BaseModel):
    locations: list[AdminLocationItem]


class AdminLocationCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str | None = None


class AdminLocationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None


class AdminLocationMutationResponse(BaseModel):
    message: str
    location: AdminLocationItem


class AdminLocationDeactivateItem(BaseModel):
    id: int
    is_active: bool


class AdminLocationDeactivateResponse(BaseModel):
    message: str
    location: AdminLocationDeactivateItem