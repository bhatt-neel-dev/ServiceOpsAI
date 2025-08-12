from fastapi import APIRouter

from api.routes.agents import agents_router
from api.routes.agents_v2 import agents_v2_router
from api.routes.health import health_router
from api.routes.playground import playground_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(agents_router)
v1_router.include_router(agents_v2_router)
v1_router.include_router(playground_router)
