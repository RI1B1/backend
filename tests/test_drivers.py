from datetime import datetime, timezone

from app.modules.drivers.models import DriverApplication
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.services.models import ServiceType
from tests.helpers import auth_header


def test_driver_application_create_and_duplicate_conflict(client, make_user):
    user = make_user()

    response = client.post(
        "/api/v1/driver/applications",
        headers=auth_header(user.id),
        json={"application_note": "Saya siap menjadi driver."},
    )

    assert response.status_code == 201
    application = response.json()["data"]
    assert application["status"] == "PENDING"
    assert application["application_note"] == "Saya siap menjadi driver."
    assert application["user"] == {"id": user.id, "name": user.name}

    duplicate = client.post(
        "/api/v1/driver/applications",
        headers=auth_header(user.id),
        json={},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DRIVER_APPLICATION_EXISTS"


def test_rejected_driver_can_submit_new_application(client, db_session, make_user):
    user = make_user()
    db_session.add(
        DriverApplication(
            user_id=user.id,
            status="REJECTED",
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/driver/applications",
        headers=auth_header(user.id),
        json={},
    )

    assert response.status_code == 201
    assert response.json()["data"]["status"] == "PENDING"
    assert response.json()["data"]["application_note"] is None


def test_get_application_returns_latest_submission(client, db_session, make_user):
    user = make_user()
    db_session.add(
        DriverApplication(
            user_id=user.id,
            status="REJECTED",
            reviewed_by=user.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    client.post(
        "/api/v1/driver/applications",
        headers=auth_header(user.id),
        json={"application_note": "Pengajuan ulang"},
    )
    response = client.get(
        "/api/v1/driver/application",
        headers=auth_header(user.id),
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "PENDING"
    assert response.json()["data"]["application_note"] == "Pengajuan ulang"


def test_driver_order_history_returns_order_contract_and_pagination(
    client,
    db_session,
    make_user,
):
    driver = make_user("DRIVER")
    customer = make_user()
    db_session.add(
        DriverApplication(
            user_id=driver.id,
            status="APPROVED",
            reviewed_by=driver.id,
            reviewed_at=datetime.now(timezone.utc),
        )
    )
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
    db_session.add_all([service_type, pickup, destination])
    db_session.flush()
    order = Order(
        customer_id=customer.id,
        driver_id=driver.id,
        service_type_id=service_type.id,
        status="COMPLETED",
        pickup_location_id=pickup.id,
        destination_location_id=destination.id,
        passenger_count=1,
    )
    db_session.add(order)
    db_session.commit()

    response = client.get(
        "/api/v1/driver/orders/history?page=1&limit=1",
        headers=auth_header(driver.id, "DRIVER"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"page": 1, "limit": 1, "total": 1}
    assert body["data"][0] == {
        "id": order.id,
        "status": "COMPLETED",
        "service_type": {
            "id": service_type.id,
            "name": "Antar-Jemput",
            "code": "ANTAR_JEMPUT",
        },
        "customer": {"id": customer.id, "name": customer.name},
        "driver": {"id": driver.id, "name": driver.name},
        "pickup_location": {
            "id": pickup.id,
            "name": pickup.name,
            "category": pickup.category,
            "latitude": pickup.latitude,
            "longitude": pickup.longitude,
        },
        "destination_location": {
            "id": destination.id,
            "name": destination.name,
            "category": destination.category,
            "latitude": destination.latitude,
            "longitude": destination.longitude,
        },
        "service_request_type": None,
        "item_description": None,
        "passenger_count": 1,
        "optional_cost_expectation": None,
        "notes": None,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }
