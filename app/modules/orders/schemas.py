"""Schema Pydantic (request/response) modul orders."""
"""Schema Pydantic (request/response) modul orders."""
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServiceTypeEnum(str, Enum):
    ANTAR_JEMPUT = "ANTAR_JEMPUT"
    JASA_TITIP = "JASA_TITIP"


class OrderStatusEnum(str, Enum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    ON_THE_WAY = "ON_THE_WAY"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderCreateRequest(BaseModel):
    service_type: ServiceTypeEnum
    pickup_location_id: int = Field(..., gt=0, description="ID lokasi awal dari katalog preset")
    destination_location_id: int = Field(..., gt=0, description="ID lokasi tujuan dari katalog preset")
    description: str = Field(..., min_length=1, description="Detail kebutuhan pesanan")
    expected_cost: int | None = Field(
        default=None,
        ge=0,
        description="Perkiraan biaya opsional, tidak boleh negatif",
    )

    @field_validator("description")
    @classmethod
    def validate_description_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Deskripsi pesanan wajib diisi dan tidak boleh kosong.")
        return cleaned


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: str
    driver_id: str | None = None
    service_type: str
    pickup_location_id: int
    destination_location_id: int
    description: str
    expected_cost: int | None = None
    status: str


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatusEnum


class OrderStatusResponse(BaseModel):
    id: int
    status: str