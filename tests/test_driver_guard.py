from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.errors import register_exception_handlers
from app.core.response import ok
from app.core.security import CurrentUser, require_approved_driver
from app.db.session import get_db
from app.modules.drivers.models import DriverApplication
from tests.helpers import auth_header


@pytest.fixture
def driver_client(db_session):
    """Aplikasi mini dengan satu route yang dilindungi require_approved_driver."""
    mini = FastAPI()
    register_exception_handlers(mini)

    @mini.get("/driver-only")
    def driver_only(user: CurrentUser = Depends(require_approved_driver)):
        return ok({"user_id": user.id})

    def override_get_db():
        yield db_session

    mini.dependency_overrides[get_db] = override_get_db
    return TestClient(mini, raise_server_exceptions=False)


def _apply(db, user, status):
    reviewed_by = user.id if status != "PENDING" else None
    reviewed_at = datetime.now(timezone.utc) if status != "PENDING" else None
    db.add(
        DriverApplication(
            user_id=user.id,
            status=status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )
    )
    db.commit()


def test_user_without_application_is_rejected(driver_client, make_user):
    user = make_user("CUSTOMER")
    res = driver_client.get("/driver-only", headers=auth_header(user.id))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "DRIVER_NOT_APPROVED"


@pytest.mark.parametrize("status", ["PENDING", "REJECTED"])
def test_pending_or_rejected_driver_is_rejected(driver_client, db_session, make_user, status):
    user = make_user("DRIVER")  # role DRIVER saja tidak cukup
    _apply(db_session, user, status)
    res = driver_client.get("/driver-only", headers=auth_header(user.id, "DRIVER"))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "DRIVER_NOT_APPROVED"


def test_approved_driver_is_allowed(driver_client, db_session, make_user):
    user = make_user("DRIVER")
    _apply(db_session, user, "APPROVED")
    res = driver_client.get("/driver-only", headers=auth_header(user.id, "DRIVER"))
    assert res.status_code == 200
    assert res.json()["data"]["user_id"] == user.id


def test_approved_but_inactive_driver_is_rejected(driver_client, db_session, make_user):
    user = make_user("DRIVER", is_active=False)
    _apply(db_session, user, "APPROVED")
    res = driver_client.get("/driver-only", headers=auth_header(user.id, "DRIVER"))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "USER_SUSPENDED"
