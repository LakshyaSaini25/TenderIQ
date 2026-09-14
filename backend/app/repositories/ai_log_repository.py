from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import pymongo
from app.core.database import db_instance

class AILogRepository:
    @property
    def collection(self):
        return db_instance.db["ai_logs"]

    def _convert_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create_indexes(self):
        await self.collection.create_index([("content_id", pymongo.ASCENDING)])
        await self.collection.create_index([("opportunity_id", pymongo.ASCENDING)])
        await self.collection.create_index([("timestamp", pymongo.DESCENDING)])

    async def log_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Logs an AI processing attempt.
        Expected keys in data:
          content_id, opportunity_id, model, processing_status,
          processing_duration, prompt_version, error, timestamp
        """
        log_entry = {
            "content_id": data.get("content_id"),
            "opportunity_id": data.get("opportunity_id"),
            "model": data.get("model"),
            "processing_status": data.get("processing_status"),
            "processing_duration": data.get("processing_duration"),
            "prompt_version": data.get("prompt_version", "v1"),
            "error": data.get("error"),
            "timestamp": data.get("timestamp") or datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(log_entry)
        doc = await self.collection.find_one({"_id": result.inserted_id})
        return self._convert_id(doc)

