from app.core.security import Role, create_access_token


def auth_header(user_id: int, role: Role | str = Role.CUSTOMER, **kwargs) -> dict:
    """Header Authorization untuk tes. `role` hanya klaim di token (server mengabaikannya)."""
    token = create_access_token(user_id, Role(role), **kwargs)
    return {"Authorization": f"Bearer {token}"}
