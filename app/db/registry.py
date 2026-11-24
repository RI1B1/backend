"""Impor semua model di sini supaya Alembic autogenerate mendeteksinya.

Setiap kali menambah models.py baru, tambahkan barisnya di bawah.
"""
from app.modules.admin import models as _admin  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.chat import models as _chat  # noqa: F401
from app.modules.drivers import models as _drivers  # noqa: F401
from app.modules.locations import models as _locations  # noqa: F401
from app.modules.orders import models as _orders  # noqa: F401
from app.modules.services import models as _services  # noqa: F401
from app.modules.users import models as _users  # noqa: F401
