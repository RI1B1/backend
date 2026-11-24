from fastapi import APIRouter, Depends

from app.core.response import ok
from app.core.security import CurrentUser, Role, require_role

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/ping", summary="Contoh role guard (hapus jika tidak perlu)")
def admin_ping(user: CurrentUser = Depends(require_role(Role.ADMIN))):
    return ok({"message": "pong", "user_id": user.id})
