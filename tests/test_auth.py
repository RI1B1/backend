from sqlalchemy import select

from app.core.config import settings
from app.core.password import hash_password
from app.modules.users.models import User

PASSWORD = "rahasia123"


def create_user(db, email="budi@mail.ugm.ac.id", role="CUSTOMER", is_active=True, password=PASSWORD):
    user = User(
        name="Budi",
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register(client, **overrides):
    payload = {"name": "Budi", "email": "budi@mail.ugm.ac.id", "password": PASSWORD}
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def login(client, email="budi@mail.ugm.ac.id", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- POST /auth/register ----------


def test_register_success(client, db_session):
    res = register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["message"] == "Registrasi berhasil"
    assert body["user"]["name"] == "Budi"
    assert body["user"]["email"] == "budi@mail.ugm.ac.id"
    assert body["user"]["role"] == "CUSTOMER"
    assert isinstance(body["user"]["id"], int)
    assert "password" not in res.text
    assert "access_token" not in body  # registrasi tidak otomatis login


def test_register_hashes_password_with_argon2id(client, db_session):
    register(client)
    user = db_session.scalar(select(User).where(User.email == "budi@mail.ugm.ac.id"))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2id$")


def test_register_ignores_role_sent_by_user(client, db_session):
    res = register(client, role="ADMIN")
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "CUSTOMER"


def test_register_normalizes_email(client, db_session):
    res = register(client, email="  Budi@MAIL.UGM.AC.ID ")
    assert res.status_code == 201
    assert res.json()["user"]["email"] == "budi@mail.ugm.ac.id"


def test_register_then_login_works(client, db_session):
    register(client)
    assert login(client).status_code == 200


def test_register_duplicate_email_returns_409(client, db_session):
    register(client)
    res = register(client, name="Orang Lain")
    assert res.status_code == 409


def test_register_duplicate_email_is_case_insensitive(client, db_session):
    register(client)
    res = register(client, email="BUDI@mail.ugm.ac.id")
    assert res.status_code == 409


def test_register_wrong_domain_returns_422(client):
    res = register(client, email="budi@gmail.com")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMAIL_DOMAIN_NOT_ALLOWED"


def test_register_lookalike_domain_is_rejected(client):
    res = register(client, email="budi@mail.ugm.ac.id.evil.com")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMAIL_DOMAIN_NOT_ALLOWED"


def test_register_malformed_email_returns_422(client):
    res = register(client, email="bukan-email")
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "email"


def test_register_short_password_returns_422(client):
    res = register(client, password="pendek")
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "password"


def test_register_blank_name_returns_422(client):
    res = register(client, name="   ")
    assert res.status_code == 422
    assert res.json()["error"]["details"][0]["field"] == "name"


def test_register_missing_fields_returns_422(client):
    res = client.post("/api/v1/auth/register", json={"email": "budi@mail.ugm.ac.id"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------- POST /auth/login ----------


def test_login_success(client, db_session):
    user = create_user(db_session)
    res = login(client)
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "Login berhasil"
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["user"] == {
        "id": user.id,
        "name": "Budi",
        "email": "budi@mail.ugm.ac.id",
        "role": "CUSTOMER",
    }


def test_login_never_returns_password_hash(client, db_session):
    create_user(db_session)
    assert "password" not in login(client).text


def test_login_email_is_case_and_space_insensitive(client, db_session):
    create_user(db_session)
    assert login(client, email="  Budi@MAIL.UGM.AC.ID ").status_code == 200


def test_login_wrong_password_returns_401(client, db_session):
    create_user(db_session)
    res = login(client, password="salah")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email_has_same_error_as_wrong_password(client, db_session):
    create_user(db_session)
    wrong_pw = login(client, password="salah").json()
    unknown = login(client, email="tidakada@mail.ugm.ac.id").json()
    assert unknown["error"]["code"] == "INVALID_CREDENTIALS"
    assert unknown == wrong_pw


def test_login_wrong_domain_returns_422(client, db_session):
    create_user(db_session)
    res = login(client, email="budi@gmail.com")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMAIL_DOMAIN_NOT_ALLOWED"


def test_login_lookalike_domain_is_rejected(client):
    res = login(client, email="budi@mail.ugm.ac.id.evil.com")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMAIL_DOMAIN_NOT_ALLOWED"


def test_login_malformed_email_returns_422(client):
    res = login(client, email="bukan-email")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_missing_fields_returns_422(client):
    res = client.post("/api/v1/auth/login", json={"email": "budi@mail.ugm.ac.id"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_suspended_user_returns_403(client, db_session):
    create_user(db_session, is_active=False)
    res = login(client)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "USER_SUSPENDED"


def test_login_suspended_user_with_wrong_password_does_not_leak_status(client, db_session):
    create_user(db_session, is_active=False)
    res = login(client, password="salah")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_returns_role_from_database(client, db_session):
    create_user(db_session, email="admin@mail.ugm.ac.id", role="ADMIN")
    res = login(client, email="admin@mail.ugm.ac.id")
    assert res.json()["user"]["role"] == "ADMIN"


# ---------- GET /auth/me ----------


def test_me_without_token_returns_401(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_invalid_token_returns_401(client):
    res = client.get("/api/v1/auth/me", headers=bearer("salah"))
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "INVALID_TOKEN"


def test_me_with_token_from_login(client, db_session):
    user = create_user(db_session)
    token = login(client).json()["access_token"]
    res = client.get("/api/v1/auth/me", headers=bearer(token))
    assert res.status_code == 200
    assert res.json() == {
        "id": user.id,
        "name": "Budi",
        "email": "budi@mail.ugm.ac.id",
        "role": "CUSTOMER",
    }


def test_me_works_for_freshly_registered_user(client, db_session):
    register(client)
    token = login(client).json()["access_token"]
    res = client.get("/api/v1/auth/me", headers=bearer(token))
    assert res.status_code == 200
    assert res.json()["email"] == "budi@mail.ugm.ac.id"


def test_me_rejects_suspended_user_with_valid_token(client, db_session):
    user = create_user(db_session)
    token = login(client).json()["access_token"]
    user.is_active = False
    db_session.commit()
    res = client.get("/api/v1/auth/me", headers=bearer(token))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "USER_SUSPENDED"
