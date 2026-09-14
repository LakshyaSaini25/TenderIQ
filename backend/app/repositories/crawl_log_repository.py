from bson import ObjectId
from datetime import datetime, timezone
from app.core.database import db_instance

class CrawlLogRepository:
    @property
    def collection(self):
        return db_instance.db["crawl_logs"]

    def _convert_id(self, doc):
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create_indexes(self):
        import pymongo
        await self.collection.create_index([("source_id", pymongo.ASCENDING)])
        await self.collection.create_index([("started_at", pymongo.DESCENDING)])

    async def create(self, log_data: dict):
        if "url" in log_data and log_data["url"]:
            log_data["url"] = str(log_data["url"])
            
        result = await self.collection.insert_one(log_data)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._convert_id(doc)

