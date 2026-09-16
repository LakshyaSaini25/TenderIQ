from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.api.router import api_router
from app.repositories.content_repository import ContentRepository
from app.repositories.crawl_log_repository import CrawlLogRepository
from app.repositories.opportunity_repository import OpportunityRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.location_repository import LocationRepository
from app.repositories.ai_log_repository import AILogRepository

import asyncio
from app.services.crawl_scheduler import get_crawl_scheduler

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event
    await connect_to_mongo()
    
    # Initialize indexes & seed initial data
    await ContentRepository().create_indexes()
    await CrawlLogRepository().create_indexes()
    await OpportunityRepository().create_indexes()
    await AILogRepository().create_indexes()
    await CategoryRepository().seed_if_empty()
    await LocationRepository().seed_if_empty()
    logger.info("MongoDB indexes verified/created & initial data seeded.")

    # Start automated crawl scheduler
    scheduler = get_crawl_scheduler()
    scheduler_task = asyncio.create_task(scheduler.start())
    logger.info("Automated Crawl Scheduler background worker launched.")
    
    yield
    # Shutdown event
    await scheduler.stop()
    try:
        scheduler_task.cancel()
        await scheduler_task
    except (asyncio.CancelledError, Exception):
        pass
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Tender & Project Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Tender & Project Intelligence API"}

