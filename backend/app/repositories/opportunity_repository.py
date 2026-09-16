from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import pymongo
from app.core.database import db_instance

class OpportunityRepository:
    @property
    def collection(self):
        return db_instance.db["opportunities"]

    def _convert_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return doc

    async def create_indexes(self):
        await self.collection.create_index([("source_id", pymongo.ASCENDING)])
        await self.collection.create_index([("content_id", pymongo.ASCENDING)])
        await self.collection.create_index([("reference_number", pymongo.ASCENDING)])
        await self.collection.create_index([("source_url", pymongo.ASCENDING)])
        await self.collection.create_index([("status", pymongo.ASCENDING)])
        await self.collection.create_index([("type", pymongo.ASCENDING)])
        await self.collection.create_index([("category_id", pymongo.ASCENDING)])
        await self.collection.create_index([("updated_at", pymongo.DESCENDING)])

    async def find_existing(self, source_id: str, reference_number: Optional[str], source_url: str) -> Optional[Dict[str, Any]]:
        """
        Find existing opportunity using deduplication strategy:
        1. source_id + reference_number (if ref number exists)
        2. source_id + source_url (if ref number is missing)
        """
        if reference_number and reference_number.strip():
            doc = await self.collection.find_one({
                "source_id": source_id,
                "reference_number": reference_number.strip()
            })
            if doc:
                return self._convert_id(doc)

        # Fallback to source_id + source_url
        doc = await self.collection.find_one({
            "source_id": source_id,
            "source_url": source_url
        })
        return self._convert_id(doc)

    async def upsert_opportunity(self, opportunity_data: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """
        Inserts or updates an opportunity document based on deduplication rules.
        Returns tuple of (status: 'CREATED' | 'UPDATED' | 'UNCHANGED', opportunity_doc)
        """
        source_id = opportunity_data.get("source_id")
        ref_num = opportunity_data.get("reference_number")
        source_url = opportunity_data.get("source_url")
        now = datetime.now(timezone.utc)

        existing = await self.find_existing(source_id, ref_num, source_url)

        if not existing:
            # Create new record
            doc_to_insert = {**opportunity_data}
            doc_to_insert["created_at"] = now
            doc_to_insert["updated_at"] = now
            result = await self.collection.insert_one(doc_to_insert)
            created_doc = await self.collection.find_one({"_id": result.inserted_id})
            return "CREATED", self._convert_id(created_doc)

        # Existing record found - check if updated
        existing_id = existing["_id"]
        fields_to_check = [
            "title", "reference_number", "reference_number_raw", "description",
            "organization", "department", "location", "category_id", "category_name",
            "value", "currency", "value_text", "published_at", "deadline",
            "contacts", "source_url", "status", "is_opportunity", "detection_reason",
            "eligibility", "requirements", "scope", "certifications",
            "experience_requirements", "equipment_requirements", "ai",
            "tender_fee", "emd_amount", "tender_category", "product_category",
            "pincode", "inviting_authority_name", "inviting_authority_address",
            "documents", "detail_solved"
        ]

        changed_fields = {}
        for field in fields_to_check:
            new_val = opportunity_data.get(field)
            old_val = existing.get(field)
            if new_val is not None and new_val != old_val:
                changed_fields[field] = new_val

        if not changed_fields:
            return "UNCHANGED", existing

        # Update changed fields
        changed_fields["updated_at"] = now
        await self.collection.update_one(
            {"_id": ObjectId(existing_id)},
            {"$set": changed_fields}
        )
        updated_doc = await self.collection.find_one({"_id": ObjectId(existing_id)})
        return "UPDATED", self._convert_id(updated_doc)

    async def create(self, opportunity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates or updates an opportunity and returns the saved document."""
        _status, doc = await self.upsert_opportunity(opportunity_data)
        return doc

    async def get_all(
        self,
        source_id: Optional[str] = None,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if source_id:
            query["source_id"] = source_id
        if type_filter:
            query["type"] = type_filter
        if status_filter:
            query["status"] = status_filter
        if category_id_filter:
            query["category_id"] = category_id_filter

        cursor = self.collection.find(query).sort("updated_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._convert_id(d) for d in docs]

    async def get_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        if not ObjectId.is_valid(opportunity_id):
            return None
        doc = await self.collection.find_one({"_id": ObjectId(opportunity_id)})
        return self._convert_id(doc)

    async def update(self, opportunity_id: str, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Patches specific fields on an existing opportunity document."""
        if not ObjectId.is_valid(opportunity_id):
            return None
        fields["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": ObjectId(opportunity_id)},
            {"$set": fields}
        )
        doc = await self.collection.find_one({"_id": ObjectId(opportunity_id)})
        return self._convert_id(doc)

    async def get_by_content_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"content_id": content_id})
        return self._convert_id(doc)

    async def count(
        self,
        source_id: Optional[str] = None,
        type_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_id_filter: Optional[str] = None
    ) -> int:
        query: Dict[str, Any] = {}
        if source_id:
            query["source_id"] = source_id
        if type_filter:
            query["type"] = type_filter
        if status_filter:
            query["status"] = status_filter
        if category_id_filter:
            query["category_id"] = category_id_filter

        return await self.collection.count_documents(query)

