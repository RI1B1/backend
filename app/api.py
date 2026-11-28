from fastapi import APIRouter

from app.health import router as health_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.chat.router import router as chat_router
from app.modules.drivers.router import router as drivers_router
from app.modules.locations.router import router as locations_router
from app.modules.orders.router import router as orders_router
from app.modules.services.router import router as services_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(services_router)
api_router.include_router(locations_router)
api_router.include_router(orders_router)
api_router.include_router(drivers_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router)
