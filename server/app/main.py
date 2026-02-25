"""AEGIS Server — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.app.core.config import get_settings
from server.app.core.exceptions import AegisException
from server.app.core.logging_config import setup_logging
from server.app.models.database.connection import Database
from server.app.api.v1.router import api_v1_router
from server.app.api.v1.websocket import ws_router
from server.app.workers.heartbeat_monitor import heartbeat_monitor_loop
from server.app.workers.scheduled_jobs import scheduled_jobs_loop

logger = logging.getLogger("aegis.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    settings = get_settings()
    setup_logging(debug=settings.debug)
    logger.info("AEGIS server starting (env=%s)", settings.env)

    # Connect databases
    await Database.connect()

    # Start background workers
    workers = [
        asyncio.create_task(heartbeat_monitor_loop()),
        asyncio.create_task(scheduled_jobs_loop()),
    ]

    logger.info("AEGIS server ready on %s:%d", settings.host, settings.port)
    yield

    # Shutdown
    logger.info("AEGIS server shutting down")
    for worker in workers:
        worker.cancel()
    await asyncio.gather(*workers, return_exceptions=True)
    await Database.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AEGIS",
        description="Accountability Engine for Goals with Integrity & Structure",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(AegisException)
    async def aegis_exception_handler(request: Request, exc: AegisException):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    # Routers
    app.include_router(api_v1_router)
    app.include_router(ws_router)

    # Root health check
    @app.get("/")
    async def root():
        return {"service": "AEGIS", "version": "0.1.0", "status": "running"}

    return app


app = create_app()
