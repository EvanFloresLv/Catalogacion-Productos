# -----------------------------------------------------------------
# Router Registration
# -----------------------------------------------------------------
from fastapi import APIRouter

from infrastructure.web.controllers.classification_controller import (
    router as classification_router,
)
from infrastructure.web.controllers.categories_controller import (
    router as categories_router,
)
from infrastructure.web.controllers.products_controller import (
    router as products_router,
)
from infrastructure.web.controllers.brands_controller import (
    router as brands_router,
)
from infrastructure.web.controllers.sql_controller import (
    router as sql_router
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(classification_router)
api_router.include_router(categories_router)
api_router.include_router(products_router)
api_router.include_router(brands_router)
api_router.include_router(sql_router)