from bson import ObjectId
from typing import List, Dict, Any, Optional
from app.core.database import db_instance
from app.processors.rules import INITIAL_CATEGORIES

class CategoryRepository:
    @property
    def collection(self):
        return db_instance.db["categories"]

    def _convert_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def seed_if_empty(self):
        count = await self.collection.count_documents({})
        if count == 0:
            for cat in INITIAL_CATEGORIES:
                parent_res = await self.collection.insert_one({"name": cat["name"], "parent_id": None})
                parent_id = str(parent_res.inserted_id)
                for child_name in cat.get("children", []):
                    await self.collection.insert_one({"name": child_name, "parent_id": parent_id})

    async def get_all() -> List[Dict[str, Any]]:
        cursor = self.collection.find().sort("name", 1)
        docs = await cursor.to_list(length=500)
        return [self._convert_id(d) for d in docs]

