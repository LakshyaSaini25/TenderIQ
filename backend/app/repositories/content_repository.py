from bson import ObjectId
from datetime import datetime, timezone
from app.core.database import db_instance

class ContentRepository:
    @property
    def collection(self):
        return db_instance.db["content"]

    def _convert_id(self, doc):
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create_indexes(self):
        import pymongo
        await self.collection.create_index([("source_id", pymongo.ASCENDING)])
        await self.collection.create_index([("url", pymongo.ASCENDING)])
        await self.collection.create_index([("content_hash", pymongo.ASCENDING)])
        await self.collection.create_index([("last_seen_at", pymongo.DESCENDING)])

    async def get_by_source_and_url(self, source_id: str, url: str):
        doc = await self.collection.find_one({"source_id": source_id, "url": url})
        return self._convert_id(doc)

    async def create(self, content_data: dict):
        now = datetime.now(timezone.utc)
        content_data["created_at"] = now
        content_data["updated_at"] = now
        content_data["url"] = str(content_data["url"])
        
        result = await self.collection.insert_one(content_data)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._convert_id(doc)

    async def update(self, content_id: str, update_data: dict):
        if not ObjectId.is_valid(content_id):
            return None
            
        update_data["updated_at"] = datetime.now(timezone.utc)
        if "url" in update_data and update_data["url"]:
            update_data["url"] = str(update_data["url"])

        result = await self.collection.update_one(
            {"_id": ObjectId(content_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None
            
        doc = await self.collection.find_one({"_id": ObjectId(content_id)})
        return self._convert_id(doc)

    async def get_all(self, skip: int = 0, limit: int = 100):
        cursor = self.collection.find().sort("last_seen_at", -1).skip(skip).limit(limit)
        contents = await cursor.to_list(length=limit)
        return [self._convert_id(c) for c in contents]

    async def get_by_id(self, content_id: str):
        if not ObjectId.is_valid(content_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(content_id)})
        return self._convert_id(doc)

    async def get_by_source(self, source_id: str, limit: int = 1000):
        cursor = self.collection.find({"source_id": source_id}).sort("last_seen_at", -1).limit(limit)
        contents = await cursor.to_list(length=limit)
        return [self._convert_id(c) for c in contents]

