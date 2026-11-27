from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
