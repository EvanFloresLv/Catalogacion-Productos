# -----------------------------------------------------------------
# FastAPI Application
# -----------------------------------------------------------------
from fastapi import FastAPI
import uvicorn

from config.logging_config import setup_logging
from infrastructure.web.routes import api_router

setup_logging()


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

if __name__ == "__main__":
    uvicorn.run("src.infrastructure.web.app:app", host="0.0.0.0", port=8000, reload=True)