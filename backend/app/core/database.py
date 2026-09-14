import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_instance = Database()

async def connect_to_mongo():
    try:
        logger.info("Connecting to MongoDB...")
        db_instance.client = AsyncIOMotorClient(settings.MONGODB_URI)
        db_instance.db = db_instance.client[settings.DATABASE_NAME]
        # Ping the database to verify connection
        await db_instance.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB!")
    except ConnectionFailure as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db_instance.client:
        logger.info("Closing MongoDB connection...")
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    return db_instance.db

