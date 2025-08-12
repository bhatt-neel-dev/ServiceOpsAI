import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api.routes.v1_router import v1_router
from api.settings import api_settings
from core.startup import initialize_tools_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting up ServiceOpsAI...")
    try:
        result = await initialize_tools_system()
        logger.info(f"Tool system initialized: {result}")
    except Exception as e:
        logger.error(f"Error initializing tool system: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ServiceOpsAI...")


def create_app() -> FastAPI:
    """Create a FastAPI App"""

    # Create FastAPI App
    app: FastAPI = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # Add v1 router
    app.include_router(v1_router)

    # Add Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create a FastAPI app
app = create_app()
