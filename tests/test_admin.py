"""Test modul Admin menggunakan data dummy — Master API Reference v1.3."""

from datetime import datetime, timezone

from app.core.security import Role, create_access_token
from app.modules.drivers.models import DriverApplication
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.services.models import ServiceType


def _auth(user_id: int, role: str = "ADMIN") -> dict[str, str]:
    token = create_access_token(user_id=user_id, role=Role(role))
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_admin_role(client, make_user):
    customer = make_user(role="CUSTOMER")
    assert client.get("/api/v1/admin/summary").status_code == 401
    assert (
        client.get("/api/v1/admin/summary", headers=_auth(customer.id, "CUSTOMER")).status_code
        == 403
    )


def test_admin_orders_and_summary(client, db_session, make_user):
    admin = make_user(role="ADMIN")
    customer = make_user(role="CUSTOMER")
    driver = make_user(role="DRIVER")
    driver.availability_status = "ACTIVE"

    db_session.add(
        DriverApplication(
            user_id=driver.id,
            status="APPROVED",
            application_note="Motor pribadi",
            reviewed_by=admin.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )

    svc_kwargs = {"name": "Antar-Jemput", "code": "ANTAR_JEMPUT"}
    if hasattr(ServiceType, "is_active"):
        svc_kwargs["is_active"] = True
    service_type = ServiceType(**svc_kwargs)

    loc1 = Location(name="Fakultas Teknik", category="KAMPUS", is_active=True)
    loc2 = Location(name="Perpustakaan Pusat", category="KAMPUS", is_active=True)
    db_session.add_all([service_type, loc1, loc2])
    db_session.commit()

    db_session.add(
        Order(
            customer_id=customer.id,
            service_type_id=service_type.id,
            status="OPEN",
            pickup_location_id=loc1.id,
            destination_location_id=loc2.id,
            passenger_count=1,
        )
    )
    db_session.commit()

    res_orders = client.get("/api/v1/admin/orders", headers=_auth(admin.id))
    assert res_orders.status_code == 200
    assert len(res_orders.json()["orders"]) == 1
    assert res_orders.json()["orders"][0]["service_type"] == "ANTAR_JEMPUT"

    res_summary = client.get("/api/v1/admin/summary", headers=_auth(admin.id))
    assert res_summary.status_code == 200
    summary = res_summary.json()["summary"]
    assert summary["total_orders"] == 1
    assert summary["open_orders"] == 1
    assert summary["active_drivers"] == 1


def test_admin_review_driver_application(client, db_session, make_user):
    admin = make_user(role="ADMIN")
    applicant = make_user(role="CUSTOMER")

    app_record = DriverApplication(
        user_id=applicant.id,
        status="PENDING",
        application_note="Beat hitam",
    )
    db_session.add(app_record)
    db_session.commit()
    db_session.refresh(app_record)

    res_list = client.get("/api/v1/admin/driver-applications", headers=_auth(admin.id))
    assert res_list.status_code == 200
    assert len(res_list.json()["applications"]) == 1

    res_approve = client.patch(
        f"/api/v1/admin/driver-applications/{app_record.id}",
        json={"status": "APPROVED"},
        headers=_auth(admin.id),
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["application"]["status"] == "APPROVED"

    db_session.refresh(applicant)
    assert applicant.role == "DRIVER"

    # Tidak boleh diproses ulang -> 409
    res_again = client.patch(
        f"/api/v1/admin/driver-applications/{app_record.id}",
        json={"status": "REJECTED"},
        headers=_auth(admin.id),
    )
    assert res_again.status_code == 409


def test_admin_locations_crud_and_deactivate(client, make_user):
    admin = make_user(role="ADMIN")
    headers = _auth(admin.id)

    res_create = client.post(
        "/api/v1/admin/locations",
        json={"name": "Fakultas Teknik", "description": "Area Fakultas Teknik"},
        headers=headers,
    )
    assert res_create.status_code == 201
    loc_id = res_create.json()["location"]["id"]

    # Duplikat -> 409
    assert (
        client.post(
            "/api/v1/admin/locations",
            json={"name": "fakultas teknik"},
            headers=headers,
        ).status_code
        == 409
    )

    res_patch = client.patch(
        f"/api/v1/admin/locations/{loc_id}",
        json={"name": "Fakultas Teknik UGM"},
        headers=headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["location"]["name"] == "Fakultas Teknik UGM"

    res_deact = client.patch(
        f"/api/v1/admin/locations/{loc_id}/deactivate",
        headers=headers,
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["location"]["is_active"] is False

    # Deactivate dua kali -> 409
    assert (
        client.patch(
            f"/api/v1/admin/locations/{loc_id}/deactivate",
            headers=headers,
        ).status_code
        == 409
    )
