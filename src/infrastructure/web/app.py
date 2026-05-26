# -----------------------------------------------------------------
# Standard Library
# -----------------------------------------------------------------
from contextlib import asynccontextmanager

# -----------------------------------------------------------------
# Third-Party
# -----------------------------------------------------------------
from fastapi import FastAPI
import uvicorn

# -----------------------------------------------------------------
# Infrastructure
# -----------------------------------------------------------------
from infrastructure.persistence.postgresql.session import (
    SessionLocal,
)

from infrastructure.persistence.postgresql.repositories.in_memory_embedding_repository import (
    InMemoryEmbeddingRepository,
)

from infrastructure.web.routes import api_router

# -----------------------------------------------------------------
# Config
# -----------------------------------------------------------------
from config.logging_config import setup_logging

setup_logging()


# -----------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    # Pre-warm the in-memory embedding cache at startup
    session = SessionLocal()
    try:
        InMemoryEmbeddingRepository(session)
        print(f"Embedding cache loaded: {len(InMemoryEmbeddingRepository._entities)} vectors")
    finally:
        session.close()

    print("Application startup completed")

    yield

    print("Application shutdown completed")


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
        host="0.0.0.0",
        port=8000,
        reload=True,
    )