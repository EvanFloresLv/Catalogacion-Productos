# -----------------------------------------------------------------
# Standard Library
# -----------------------------------------------------------------
import logging
from contextlib import asynccontextmanager

# -----------------------------------------------------------------
# Third-Party
# -----------------------------------------------------------------
from fastapi import FastAPI
import uvicorn

# -----------------------------------------------------------------
# Infrastructure
# -----------------------------------------------------------------
from infrastructure.embeddings.singleton import warmup_clients

from infrastructure.web.routes import api_router

# -----------------------------------------------------------------
# Config
# -----------------------------------------------------------------
from config.logging_config import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm the embedding model + log the embedding table size."""
    logger.info("Starting application…")

    try:
        warmup_clients(embedding_dim=768)
        logger.info("Shared embedding client warmed up")
    except Exception as e:
        logger.warning(
            "Failed to warm up embedding client (%s); first request will pay cold-start",
            e,
        )

    yield

    logger.info("Application shutdown completed")


# -----------------------------------------------------------------
# FastAPI Factory
# -----------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="Product Routing API",
        description="Product classification and category management API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router)

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    return app


# -----------------------------------------------------------------
# Application Instance
# -----------------------------------------------------------------
app = create_app()


# -----------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------
if __name__ == "__main__":

    uvicorn.run(
        "src.infrastructure.web.app:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
    )
