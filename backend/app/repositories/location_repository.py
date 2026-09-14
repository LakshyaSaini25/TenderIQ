from bson import ObjectId
from typing import List, Dict, Any, Optional
from app.core.database import db_instance
from app.processors.rules import INITIAL_LOCATIONS

class LocationRepository:
    @property
    def collection(self):
        return db_instance.db["locations"]

    def _convert_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def seed_if_empty(self):
        count = await self.collection.count_documents({})
        if count == 0:
            for country_data in INITIAL_LOCATIONS:
                country_name = country_data["country"]
                for state_data in country_data.get("states", []):
                    state_name = state_data["state"]
                    for city_name in state_data.get("cities", []):
                        await self.collection.insert_one({
                            "country": country_name,
                            "state": state_name,
                            "city": city_name
                        })

    async def get_all(self) -> List[Dict[str, Any]]:
        cursor = self.collection.find().sort("state", 1)
        docs = await cursor.to_list(length=1000)
        return [self._convert_id(d) for d in docs]

