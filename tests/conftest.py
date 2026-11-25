import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import registry  # noqa: F401  (memuat semua model agar create_all membuat semua tabel)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.users.models import User


@pytest.fixture
def db_session():
    """Database SQLite in-memory baru untuk setiap tes (tidak butuh Postgres)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session):
    """Pabrik user: make_user(role="ADMIN", is_active=True) -> User."""
    counter = {"n": 0}

    def _make(role: str = "CUSTOMER", is_active: bool = True) -> User:
        counter["n"] += 1
        user = User(
            name=f"User {counter['n']}",
            email=f"user{counter['n']}@mail.ugm.ac.id",
            password_hash="hash-palsu-untuk-tes",
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make
