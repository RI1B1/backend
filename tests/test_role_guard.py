from tests.helpers import auth_header


def test_no_token_returns_401(client):
    res = client.get("/api/v1/admin/ping")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token_returns_401(client):
    res = client.get("/api/v1/admin/ping", headers={"Authorization": "Bearer salah"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


def test_expired_token_returns_401(client, make_user):
    user = make_user("ADMIN")
    res = client.get("/api/v1/admin/ping", headers=auth_header(user.id, "ADMIN", expires_minutes=-1))
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "TOKEN_EXPIRED"


def test_token_for_unknown_user_returns_401(client):
    res = client.get("/api/v1/admin/ping", headers=auth_header(9999, "ADMIN"))
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


def test_wrong_role_returns_403(client, make_user):
    user = make_user("CUSTOMER")
    res = client.get("/api/v1/admin/ping", headers=auth_header(user.id, "CUSTOMER"))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_allowed(client, make_user):
    user = make_user("ADMIN")
    res = client.get("/api/v1/admin/ping", headers=auth_header(user.id, "ADMIN"))
    assert res.status_code == 200
    assert res.json()["data"]["user_id"] == user.id


def test_role_is_read_from_db_not_from_token(client, make_user):
    """Token mengaku ADMIN, tetapi di DB user hanyalah CUSTOMER -> harus ditolak."""
    user = make_user("CUSTOMER")
    res = client.get("/api/v1/admin/ping", headers=auth_header(user.id, "ADMIN"))
    assert res.status_code == 403


def test_inactive_user_is_rejected(client, make_user):
    user = make_user("ADMIN", is_active=False)
    res = client.get("/api/v1/admin/ping", headers=auth_header(user.id, "ADMIN"))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "USER_SUSPENDED"
