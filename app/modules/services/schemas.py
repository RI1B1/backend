"""Schema Pydantic (request/response) modul services."""
"""Schema Pydantic (request/response) modul services."""
from pydantic import BaseModel, ConfigDict


class ServiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str


class ServiceListPayload(BaseModel):
    services: list[ServiceItemResponse]