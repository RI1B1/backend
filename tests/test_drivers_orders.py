from datetime import datetime, timezone

from sqlalchemy import select

from app.modules.drivers.models import DriverApplication
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.orders.status_models import OrderStatusLog
from app.modules.services.models import ServiceType
from tests.helpers import auth_header


def _approved_driver(db, make_user, availability="ACTIVE"):
    admin = make_user("ADMIN")
    driver = make_user("DRIVER")
    db.add(
        DriverApplication(
            user_id=driver.id,
            status="APPROVED",
            reviewed_by=admin.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    driver.availability_status = availability
    db.commit()
    return driver


def _seed_refs(db):
    service_type = ServiceType(name="Antar-Jemput", code="ANTAR_JEMPUT")
    pickup = Location(
        name="Perpustakaan Pusat UGM",
        category="KAMPUS",
        latitude=-7.7712,
        longitude=110.3775,
    )
    destination = Location(
        name="Gedung Pusat UGM",
        category="KAMPUS",
        latitude=-7.7700,
        longitude=110.3770,
    )
    db.add_all([service_type, pickup, destination])
    db.flush()
    return service_type, pickup, destination


def _make_order(db, customer, refs, status="OPEN"):
    service_type, pickup, destination = refs
    order = Order(
        customer_id=customer.id,
        service_type_id=service_type.id,
        status=status,
        pickup_location_id=pickup.id,
        destination_location_id=destination.id,
        passenger_count=1,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


# ---------------------------------------------------------------- availability (v1.3 8.4, 8.5)


def test_get_availability_returns_plain_shape(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user, availability="INACTIVE")

    res = client.get("/api/v1/driver/availability", headers=auth_header(driver.id, "DRIVER"))

    assert res.status_code == 200
    assert res.json() == {"availability": "INACTIVE"}


def test_patch_availability_returns_message_and_new_value(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user, availability="INACTIVE")
    headers = auth_header(driver.id, "DRIVER")

    res = client.patch("/api/v1/driver/availability", json={"availability": "ACTIVE"}, headers=headers)

    assert res.status_code == 200
    assert res.json() == {
        "message": "Availability berhasil diperbarui",
        "availability": "ACTIVE",
    }
    after = client.get("/api/v1/driver/availability", headers=headers)
    assert after.json() == {"availability": "ACTIVE"}


def test_patch_availability_rejects_old_field_name(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user)

    res = client.patch(
        "/api/v1/driver/availability",
        json={"availability_status": "INACTIVE"},
        headers=auth_header(driver.id, "DRIVER"),
    )

    assert res.status_code == 422


def test_patch_availability_rejects_invalid_value(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user)

    res = client.patch(
        "/api/v1/driver/availability",
        json={"availability": "BUSY"},
        headers=auth_header(driver.id, "DRIVER"),
    )

    assert res.status_code == 422


def test_availability_requires_approved_driver(client, make_user):
    user = make_user("DRIVER")  # belum punya pengajuan APPROVED

    res = client.get("/api/v1/driver/availability", headers=auth_header(user.id, "DRIVER"))

    assert res.status_code == 403


# ---------------------------------------------------------------- orders/available (v1.3 7.3)


def test_available_orders_lists_only_open_orders(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user)
    customer = make_user()
    refs = _seed_refs(db_session)
    open_order = _make_order(db_session, customer, refs, status="OPEN")
    _make_order(db_session, customer, refs, status="CANCELLED")

    res = client.get("/api/v1/orders/available", headers=auth_header(driver.id, "DRIVER"))

    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["total"] == 1
    assert [item["id"] for item in body["data"]] == [open_order.id]


# ---------------------------------------------------------------- orders/{id}/accept (v1.3 7.5)


def test_accept_order_success(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user)
    customer = make_user()
    order = _make_order(db_session, customer, _seed_refs(db_session))

    res = client.post(
        f"/api/v1/orders/{order.id}/accept",
        headers=auth_header(driver.id, "DRIVER"),
    )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "ACCEPTED"
    assert data["driver"]["id"] == driver.id
    db_session.refresh(order)
    assert order.status == "ACCEPTED"
    assert order.driver_id == driver.id
    logs = db_session.scalars(
        select(OrderStatusLog).where(
            OrderStatusLog.order_id == order.id,
            OrderStatusLog.new_status == "ACCEPTED",
        )
    ).all()
    assert len(logs) == 1


def test_accept_order_already_taken_by_another_driver(client, db_session, make_user):
    first = _approved_driver(db_session, make_user)
    second = _approved_driver(db_session, make_user)
    customer = make_user()
    order = _make_order(db_session, customer, _seed_refs(db_session))

    ok_res = client.post(
        f"/api/v1/orders/{order.id}/accept",
        headers=auth_header(first.id, "DRIVER"),
    )
    late_res = client.post(
        f"/api/v1/orders/{order.id}/accept",
        headers=auth_header(second.id, "DRIVER"),
    )

    assert ok_res.status_code == 200
    assert late_res.status_code == 409
    assert late_res.json()["error"]["code"] == "ORDER_ALREADY_TAKEN"
    db_session.refresh(order)
    assert order.driver_id == first.id


def test_accept_order_rejects_inactive_driver(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user, availability="INACTIVE")
    customer = make_user()
    order = _make_order(db_session, customer, _seed_refs(db_session))

    res = client.post(
        f"/api/v1/orders/{order.id}/accept",
        headers=auth_header(driver.id, "DRIVER"),
    )

    assert res.status_code == 403
    db_session.refresh(order)
    assert order.status == "OPEN"
    assert order.driver_id is None


def test_accept_order_not_found(client, db_session, make_user):
    driver = _approved_driver(db_session, make_user)

    res = client.post("/api/v1/orders/9999/accept", headers=auth_header(driver.id, "DRIVER"))

    assert res.status_code == 404
