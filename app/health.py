from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.response import ok
from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Cek app dan koneksi database")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        database = "up"
    except Exception:
        database = "down"
    return ok({"status": "ok", "database": database})
