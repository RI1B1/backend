from app.core.security import Role, create_access_token


def _auth(role: Role) -> dict:
    return {"Authorization": f"Bearer {create_access_token('u1', role)}"}


def test_no_token_returns_401(client):
    res = client.get("/api/v1/admin/ping")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token_returns_401(client):
    res = client.get("/api/v1/admin/ping", headers={"Authorization": "Bearer salah"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


def test_wrong_role_returns_403(client):
    res = client.get("/api/v1/admin/ping", headers=_auth(Role.CUSTOMER))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_allowed(client):
    res = client.get("/api/v1/admin/ping", headers=_auth(Role.ADMIN))
    assert res.status_code == 200
    assert res.json()["data"]["message"] == "pong"
