from app.modules.locations.models import Location
from tests.helpers import auth_header


def _create_location(
    db_session, name: str, *, is_active: bool = True, description: str | None = None
) -> Location:
    location = Location(
        name=name,
        category="KAMPUS",
        latitude=-7.77,
        longitude=110.37,
        description=description,
        is_active=is_active,
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)
    return location


def _admin_headers(make_user) -> dict:
    admin = make_user("ADMIN")
    return auth_header(admin.id, "ADMIN")


# ------------------------------------------------------------ GET /admin/locations (11.5)


def test_admin_list_requires_login(client):
    res = client.get("/api/v1/admin/locations")
    assert res.status_code == 401


def test_admin_list_forbidden_for_non_admin(client, make_user):
    for role in ("CUSTOMER", "DRIVER"):
        user = make_user(role)
        res = client.get("/api/v1/admin/locations", headers=auth_header(user.id, role))
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_list_includes_inactive_locations(client, db_session, make_user):
    active = _create_location(db_session, "Fakultas Teknik", description="Area Fakultas Teknik")
    inactive = _create_location(db_session, "Lokasi nonaktif", is_active=False)

    res = client.get("/api/v1/admin/locations", headers=_admin_headers(make_user))

    assert res.status_code == 200
    body = res.json()
    assert list(body.keys()) == ["locations"]
    assert body["locations"] == [
        {
            "id": active.id,
            "name": "Fakultas Teknik",
            "description": "Area Fakultas Teknik",
            "is_active": True,
        },
        {"id": inactive.id, "name": "Lokasi nonaktif", "description": None, "is_active": False},
    ]


# ------------------------------------------- PATCH /admin/locations/{location_id} (11.7)


def test_admin_update_requires_login(client, db_session):
    location = _create_location(db_session, "Fakultas Teknik")
    res = client.patch(f"/api/v1/admin/locations/{location.id}", json={"name": "Baru"})
    assert res.status_code == 401


def test_admin_update_forbidden_for_non_admin(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik")
    user = make_user("CUSTOMER")
    res = client.patch(
        f"/api/v1/admin/locations/{location.id}",
        json={"name": "Baru"},
        headers=auth_header(user.id),
    )
    assert res.status_code == 403
    db_session.refresh(location)
    assert location.name == "Fakultas Teknik"


def test_admin_update_name_and_description(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik", description="Area lama")

    res = client.patch(
        f"/api/v1/admin/locations/{location.id}",
        json={"name": "Fakultas Teknik UGM", "description": "Area Fakultas Teknik"},
        headers=_admin_headers(make_user),
    )

    assert res.status_code == 200
    assert res.json() == {
        "message": "Lokasi berhasil diperbarui",
        "location": {
            "id": location.id,
            "name": "Fakultas Teknik UGM",
            "description": "Area Fakultas Teknik",
            "is_active": True,
        },
    }
    db_session.refresh(location)
    assert location.name == "Fakultas Teknik UGM"


def test_admin_update_partial_keeps_other_fields(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik", description="Area lama")

    res = client.patch(
        f"/api/v1/admin/locations/{location.id}",
        json={"description": "Deskripsi baru"},
        headers=_admin_headers(make_user),
    )

    assert res.status_code == 200
    assert res.json()["location"]["name"] == "Fakultas Teknik"
    assert res.json()["location"]["description"] == "Deskripsi baru"


def test_admin_update_does_not_change_is_active(client, db_session, make_user):
    location = _create_location(db_session, "Lokasi nonaktif", is_active=False)

    res = client.patch(
        f"/api/v1/admin/locations/{location.id}",
        json={"name": "Nama baru", "is_active": True},
        headers=_admin_headers(make_user),
    )

    assert res.status_code == 200
    assert res.json()["location"]["is_active"] is False


def test_admin_update_not_found_returns_404(client, make_user):
    res = client.patch(
        "/api/v1/admin/locations/9999",
        json={"name": "Baru"},
        headers=_admin_headers(make_user),
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "LOCATION_NOT_FOUND"


def test_admin_update_invalid_input_returns_422(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik")
    headers = _admin_headers(make_user)
    url = f"/api/v1/admin/locations/{location.id}"

    for payload in (
        {},  # tidak ada field yang diisi
        {"name": ""},
        {"name": "   "},
        {"name": None},
        {"name": "x" * 151},
        {"name": 123},
    ):
        res = client.patch(url, json=payload, headers=headers)
        assert res.status_code == 422, payload
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"

    db_session.refresh(location)
    assert location.name == "Fakultas Teknik"


# ------------------------------------ PATCH /admin/locations/{location_id}/deactivate (11.8)


def test_admin_deactivate_requires_login(client, db_session):
    location = _create_location(db_session, "Fakultas Teknik")
    res = client.patch(f"/api/v1/admin/locations/{location.id}/deactivate")
    assert res.status_code == 401


def test_admin_deactivate_forbidden_for_non_admin(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik")
    user = make_user("DRIVER")
    res = client.patch(
        f"/api/v1/admin/locations/{location.id}/deactivate",
        headers=auth_header(user.id, "DRIVER"),
    )
    assert res.status_code == 403
    db_session.refresh(location)
    assert location.is_active is True


def test_admin_deactivate_success(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik")

    res = client.patch(
        f"/api/v1/admin/locations/{location.id}/deactivate",
        headers=_admin_headers(make_user),
    )

    assert res.status_code == 200
    assert res.json() == {
        "message": "Lokasi berhasil dinonaktifkan",
        "location": {"id": location.id, "is_active": False},
    }
    db_session.refresh(location)
    assert location.is_active is False


def test_admin_deactivate_twice_returns_409(client, db_session, make_user):
    location = _create_location(db_session, "Fakultas Teknik", is_active=False)

    res = client.patch(
        f"/api/v1/admin/locations/{location.id}/deactivate",
        headers=_admin_headers(make_user),
    )

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"


def test_admin_deactivate_not_found_returns_404(client, make_user):
    res = client.patch(
        "/api/v1/admin/locations/9999/deactivate",
        headers=_admin_headers(make_user),
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "LOCATION_NOT_FOUND"


def test_deactivated_location_is_hidden_from_public_list_but_not_deleted(
    client, db_session, make_user
):
    location = _create_location(db_session, "Fakultas Teknik")
    admin_headers = _admin_headers(make_user)

    client.patch(f"/api/v1/admin/locations/{location.id}/deactivate", headers=admin_headers)

    public = client.get("/api/v1/locations", headers=admin_headers)
    assert public.json()["locations"] == []

    admin_list = client.get("/api/v1/admin/locations", headers=admin_headers)
    assert [item["id"] for item in admin_list.json()["locations"]] == [location.id]
    assert admin_list.json()["locations"][0]["is_active"] is False
