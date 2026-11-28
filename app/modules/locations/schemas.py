"""Schema Pydantic (response) modul locations.

Bentuk respons mengikuti Master API Reference v1.3 bagian 6:
id, name, description, is_active.
category/latitude/longitude sengaja tidak dikembalikan (tidak ada di kontrak v1.3).

Endpoint Admin lokasi (bagian 11.5-11.8) berada di modul admin.
"""

from pydantic import BaseModel, ConfigDict


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool


class LocationListResponse(BaseModel):
    locations: list[LocationOut]
