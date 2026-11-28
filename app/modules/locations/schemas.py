"""Schema Pydantic (request/response) modul locations.

Bentuk respons mengikuti Master API Reference v1.3 bagian 6 dan 11.5-11.8:
id, name, description, is_active.
category/latitude/longitude sengaja tidak dikembalikan (tidak ada di kontrak v1.3).
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool


class LocationListResponse(BaseModel):
    locations: list[LocationOut]


# ---------------------------------------------------------------- Admin (11.5 - 11.8)


class LocationUpdateIn(BaseModel):
    """Body PATCH /admin/locations/{location_id} (11.7).

    Hanya name dan description. Field boleh dikirim sebagian ("sesuai kebutuhan"),
    tetapi minimal satu harus ada. Field lain di body diabaikan.
    """

    name: str | None = Field(default=None, max_length=150)  # String(150) di tabel locations
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Nama lokasi tidak boleh kosong.")
        return value

    @model_validator(mode="after")
    def _require_at_least_one_field(self):
        sent = self.model_fields_set & {"name", "description"}
        if not sent:
            raise ValueError("Minimal satu field (name atau description) harus diisi.")
        if "name" in sent and self.name is None:
            raise ValueError("Nama lokasi tidak boleh kosong.")
        return self


class LocationUpdateResponse(BaseModel):
    message: str
    location: LocationOut


class LocationDeactivatedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class LocationDeactivateResponse(BaseModel):
    message: str
    location: LocationDeactivatedOut
