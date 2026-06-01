"""KnowledgePilot AI - FastAPI Application Entry Point."""

import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.db.database import init_db

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    setup_logging()
    logger.info("Starting KnowledgePilot AI", version="1.0.0")
    
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    logger.info("Shutting down KnowledgePilot AI")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise Personal Knowledge Base powered by RAG",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Include API Router
    app.include_router(api_router, prefix=f"/api/{settings.api_version}")

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": "1.0.0",
            "environment": settings.app_env,
        }

    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint."""
        return {
            "message": "Welcome to KnowledgePilot AI",
            "docs": "/api/docs",
            "health": "/health",
        }

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
    )
