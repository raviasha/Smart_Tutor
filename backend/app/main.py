import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import supabase
from app.routes import videos, transcripts, qa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up Smart Tutor API...")
    # Verify Supabase connection
    try:
        result = supabase.table("videos").select("id").limit(1).execute()
        logger.info("Supabase connection verified.")
    except Exception as e:
        logger.warning(f"Supabase connection check: {e} (tables may not exist yet)")
    yield
    logger.info("Shutting down Smart Tutor API...")


app = FastAPI(
    title="Smart Tutor API",
    description="Audio-first AI tutor for YouTube educational videos",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(videos.router, prefix="/api")
app.include_router(transcripts.router, prefix="/api")
app.include_router(qa.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Smart Tutor API is running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
