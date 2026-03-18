"""Application entry point — FastAPI app factory."""

from fastapi import FastAPI

from quote_agent.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        debug=settings.app.debug,
    )

    return app
