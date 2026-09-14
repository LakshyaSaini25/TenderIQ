from bson import ObjectId
from datetime import datetime, timezone
from app.core.database import db_instance

class SourceRepository:
    @property
    def collection(self):
        return db_instance.db["sources"]

    def _convert_id(self, doc):
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def get_all(self):
        cursor = self.collection.find().sort("created_at", -1)
        sources = await cursor.to_list(length=1000)
        return [self._convert_id(s) for s in sources]

    async def get_by_id(self, source_id: str):
        if not ObjectId.is_valid(source_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(source_id)})
        return self._convert_id(doc)

    async def create(self, source_data: dict):
        now = datetime.now(timezone.utc)
        source_data["created_at"] = now
        source_data["updated_at"] = now
        source_data["last_checked_at"] = None
        source_data["url"] = str(source_data["url"])
        
        result = await self.collection.insert_one(source_data)
        return await self.get_by_id(str(result.inserted_id))

    async def update(self, source_id: str, update_data: dict):
        if not ObjectId.is_valid(source_id):
            return None
            
        update_data["updated_at"] = datetime.now(timezone.utc)
        if "url" in update_data and update_data["url"]:
            update_data["url"] = str(update_data["url"])

        result = await self.collection.update_one(
            {"_id": ObjectId(source_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            return None
            
        return await self.get_by_id(source_id)

    async def delete(self, source_id: str):
        if not ObjectId.is_valid(source_id):
            return False
        result = await self.collection.delete_one({"_id": ObjectId(source_id)})
        return result.deleted_count > 0

