# -----------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------
from fastapi import FastAPI

from infrastructure.web.routes import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Product Routing API",
        description="Product classification and category management API",
        version="0.1.0",
    )

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
