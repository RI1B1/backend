from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.modules.drivers.models import DriverApplication
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.orders.status_models import OrderStatusLog
from app.modules.services.models import ServiceType
from tests.helpers import auth_header


def _create_location(db_session, name: str, *, is_active: bool = True) -> Location:
    location = Location(
        name=name,
        category="KAMPUS",
        latitude=-7.77,
        longitude=110.37,
        is_active=is_active,
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)
    return location


def _create_service(db_session, code: str) -> ServiceType:
    service = ServiceType(name=code, code=code, is_active=True)
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    return service


def _create_order(
    db_session,
    customer_id: int,
    service_type_id: int,
    pickup_location_id: int,
    destination_location_id: int,
    *,
    driver_id: int | None = None,
    status: str = "OPEN",
) -> Order:
    order = Order(
        customer_id=customer_id,
        driver_id=driver_id,
        service_type_id=service_type_id,
        pickup_location_id=pickup_location_id,
        destination_location_id=destination_location_id,
        status=status,
        notes="Antar ke tujuan",
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    return order


@pytest.mark.parametrize("service_type", ["ANTAR_JEMPUT", "JASA_TITIP"])
def test_create_order_maps_api_fields_to_existing_model(
    client, db_session, make_user, service_type
):
    customer = make_user("CUSTOMER")
    service = _create_service(db_session, service_type)
    pickup = _create_location(db_session, "Fakultas Teknik")
    destination = _create_location(db_session, "Perpustakaan")

    response = client.post(
        "/api/v1/orders",
        headers=auth_header(customer.id),
        json={
            "service_type": service_type,
            "pickup_location_id": pickup.id,
            "destination_location_id": destination.id,
            "description": "  Pesanan percobaan  ",
            "expected_cost": 12500,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Order berhasil dibuat"
    assert body["order"] == {
        "id": body["order"]["id"],
        "customer_id": customer.id,
        "driver_id": None,
        "service_type": service.code,
        "pickup_location_id": pickup.id,
        "destination_location_id": destination.id,
        "description": "Pesanan percobaan",
        "expected_cost": 12500,
        "status": "OPEN",
    }

    stored = db_session.get(Order, body["order"]["id"])
    assert stored.optional_cost_expectation == Decimal("12500.00")
    assert stored.notes == ("Pesanan percobaan" if service_type == "ANTAR_JEMPUT" else None)
    assert stored.item_description == (
        "Pesanan percobaan" if service_type == "JASA_TITIP" else None
    )
    assert stored.service_request_type is None
    log = db_session.query(OrderStatusLog).filter_by(order_id=stored.id).one()
    assert log.old_status is None
    assert log.new_status == "OPEN"
    assert log.changed_by == customer.id


def test_create_order_rejects_inactive_location(client, make_user, db_session):
    customer = make_user("CUSTOMER")
    _create_service(db_session, "ANTAR_JEMPUT")
    pickup = _create_location(db_session, "Fakultas Teknik")
    destination = _create_location(db_session, "Lokasi nonaktif", is_active=False)

    response = client.post(
        "/api/v1/orders",
        headers=auth_header(customer.id),
        json={
            "service_type": "ANTAR_JEMPUT",
            "pickup_location_id": pickup.id,
            "destination_location_id": destination.id,
            "description": "Antar ke tujuan",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LOCATION_INACTIVE"


def test_create_order_rejects_identical_locations(client, make_user, db_session):
    customer = make_user("CUSTOMER")
    _create_service(db_session, "ANTAR_JEMPUT")
    location = _create_location(db_session, "Fakultas Teknik")

    response = client.post(
        "/api/v1/orders",
        headers=auth_header(customer.id),
        json={
            "service_type": "ANTAR_JEMPUT",
            "pickup_location_id": location.id,
            "destination_location_id": location.id,
            "description": "Antar ke tujuan",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("expected_cost", ["10000000000", "1.234"])
def test_create_order_rejects_cost_outside_database_precision(
    client, make_user, expected_cost
):
    customer = make_user("CUSTOMER")

    response = client.post(
        "/api/v1/orders",
        headers=auth_header(customer.id),
        json={
            "service_type": "ANTAR_JEMPUT",
            "pickup_location_id": 1,
            "destination_location_id": 2,
            "description": "Antar ke tujuan",
            "expected_cost": expected_cost,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_customer_can_only_see_their_own_orders(client, db_session, make_user):
    customer = make_user("CUSTOMER")
    other_customer = make_user("CUSTOMER")
    service = _create_service(db_session, "ANTAR_JEMPUT")
    pickup = _create_location(db_session, "Fakultas Teknik")
    destination = _create_location(db_session, "Perpustakaan")
    own_order = _create_order(
        db_session, customer.id, service.id, pickup.id, destination.id
    )
    other_order = _create_order(
        db_session, other_customer.id, service.id, pickup.id, destination.id
    )

    response = client.get("/api/v1/orders/my", headers=auth_header(customer.id))
    assert response.status_code == 200
    assert [order["id"] for order in response.json()["orders"]] == [own_order.id]

    forbidden = client.get(
        f"/api/v1/orders/{other_order.id}",
        headers=auth_header(customer.id),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ORDER_ACCESS_DENIED"


def test_assigned_approved_driver_can_update_order_status(
    client, db_session, make_user
):
    customer = make_user("CUSTOMER")
    driver = make_user("DRIVER")
    reviewer = make_user("ADMIN")
    db_session.add(
        DriverApplication(
            user_id=driver.id,
            status="APPROVED",
            reviewed_by=reviewer.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()
    service = _create_service(db_session, "ANTAR_JEMPUT")
    pickup = _create_location(db_session, "Fakultas Teknik")
    destination = _create_location(db_session, "Perpustakaan")
    order = _create_order(
        db_session,
        customer.id,
        service.id,
        pickup.id,
        destination.id,
        driver_id=driver.id,
        status="ACCEPTED",
    )

    first = client.patch(
        f"/api/v1/orders/{order.id}/status",
        headers=auth_header(driver.id, "DRIVER"),
        json={"status": "ON_THE_WAY"},
    )
    assert first.status_code == 200
    assert first.json()["order"]["status"] == "ON_THE_WAY"

    second = client.patch(
        f"/api/v1/orders/{order.id}/status",
        headers=auth_header(driver.id, "DRIVER"),
        json={"status": "COMPLETED"},
    )
    assert second.status_code == 200
    assert second.json()["order"]["status"] == "COMPLETED"

    invalid_transition = client.patch(
        f"/api/v1/orders/{order.id}/status",
        headers=auth_header(driver.id, "DRIVER"),
        json={"status": "ON_THE_WAY"},
    )
    assert invalid_transition.status_code == 409
    assert invalid_transition.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    history = client.get(
        f"/api/v1/orders/{order.id}/status-history",
        headers=auth_header(customer.id),
    )
    assert [entry["status"] for entry in history.json()["status_history"]] == [
        "ON_THE_WAY",
        "COMPLETED",
    ]


def test_customer_can_cancel_only_open_order(client, db_session, make_user):
    customer = make_user("CUSTOMER")
    service = _create_service(db_session, "ANTAR_JEMPUT")
    pickup = _create_location(db_session, "Fakultas Teknik")
    destination = _create_location(db_session, "Perpustakaan")
    order = _create_order(
        db_session, customer.id, service.id, pickup.id, destination.id
    )

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_header(customer.id),
    )
    assert response.status_code == 200
    assert response.json()["order"]["status"] == "CANCELLED"

    repeated = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_header(customer.id),
    )
    assert repeated.status_code == 409
    assert repeated.json()["error"]["code"] == "ORDER_NOT_CANCELLABLE"
