from app.modules.locations.models import Location
from tests.helpers import auth_header

LOCATION_FIELDS = {"id", "name", "description", "is_active"}


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


def test_list_locations_requires_login(client):
    res = client.get("/api/v1/locations")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_list_locations_returns_only_active(client, db_session, make_user):
    user = make_user("CUSTOMER")
    active = _create_location(db_session, "Fakultas Teknik", description="Area Fakultas Teknik")
    _create_location(db_session, "Lokasi nonaktif", is_active=False)

    res = client.get("/api/v1/locations", headers=auth_header(user.id))

    assert res.status_code == 200
    body = res.json()
    assert list(body.keys()) == ["locations"]
    assert body["locations"] == [
        {
            "id": active.id,
            "name": "Fakultas Teknik",
            "description": "Area Fakultas Teknik",
            "is_active": True,
        }
    ]


def test_list_locations_hides_internal_fields(client, db_session, make_user):
    user = make_user("CUSTOMER")
    _create_location(db_session, "Perpustakaan Pusat")

    res = client.get("/api/v1/locations", headers=auth_header(user.id))

    assert set(res.json()["locations"][0].keys()) == LOCATION_FIELDS


def test_list_locations_allowed_for_driver_and_admin(client, db_session, make_user):
    _create_location(db_session, "Fakultas Teknik")
    for role in ("DRIVER", "ADMIN"):
        user = make_user(role)
        res = client.get("/api/v1/locations", headers=auth_header(user.id, role))
        assert res.status_code == 200


def test_get_location_detail(client, db_session, make_user):
    user = make_user("CUSTOMER")
    location = _create_location(db_session, "Fakultas Teknik", description="Area Fakultas Teknik")

    res = client.get(f"/api/v1/locations/{location.id}", headers=auth_header(user.id))

    assert res.status_code == 200
    assert res.json() == {
        "id": location.id,
        "name": "Fakultas Teknik",
        "description": "Area Fakultas Teknik",
        "is_active": True,
    }


def test_get_location_detail_requires_login(client, db_session):
    location = _create_location(db_session, "Fakultas Teknik")
    res = client.get(f"/api/v1/locations/{location.id}")
    assert res.status_code == 401


def test_get_location_not_found_returns_404(client, make_user):
    user = make_user("CUSTOMER")
    res = client.get("/api/v1/locations/9999", headers=auth_header(user.id))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "LOCATION_NOT_FOUND"
