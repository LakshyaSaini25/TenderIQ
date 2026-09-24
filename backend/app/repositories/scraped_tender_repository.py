from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
import pymongo
import re

from app.core.database import db_instance
from app.scrapers.schema import TenderSchema, TenderFilterParams


class ScrapedTenderRepository:
    """
    MongoDB repository for managing scraped and normalized tenders in the 'scraped_tenders' collection.
    """

    @property
    def collection(self):
        return db_instance.db["scraped_tenders"]

    def _convert_id(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        doc["id"] = str(doc["_id"])
        doc["_id"] = str(doc["_id"])
        return doc

    async def create_indexes(self):
        """
        Creates necessary indexes including unique deduplication constraints.
        """
        # Unique deduplication index on source + source_id
        await self.collection.create_index(
            [("source", pymongo.ASCENDING), ("source_id", pymongo.ASCENDING)],
            unique=True,
            name="uniq_source_source_id"
        )
        # Search & filter indexes
        await self.collection.create_index([("reference_no", pymongo.ASCENDING)])
        await self.collection.create_index([("source", pymongo.ASCENDING)])
        await self.collection.create_index([("status", pymongo.ASCENDING)])
        await self.collection.create_index([("category", pymongo.ASCENDING)])
        await self.collection.create_index([("location", pymongo.ASCENDING)])
        await self.collection.create_index([("organisation", pymongo.ASCENDING)])
        await self.collection.create_index([("closing_date", pymongo.ASCENDING)])
        await self.collection.create_index([("publication_date", pymongo.DESCENDING)])
        await self.collection.create_index([("tender_value", pymongo.DESCENDING)])
        await self.collection.create_index([("scraped_at", pymongo.DESCENDING)])

    async def upsert_tender(self, tender: TenderSchema) -> Tuple[bool, str]:
        """
        Inserts new tender or updates existing one based on (source, source_id).
        Returns: (is_new: bool, tender_id: str)
        """
        now = datetime.now(timezone.utc)
        data = tender.model_dump()
        data["updated_at"] = now

        existing = await self.collection.find_one({
            "source": tender.source,
            "source_id": tender.source_id
        })

        if existing:
            # Preserve original scraped_at timestamp
            data["scraped_at"] = existing.get("scraped_at", now)
            # If the new data doesn't have details solved but existing did, preserve solved details
            if not data.get("detail_solved") and existing.get("detail_solved"):
                data["detail_solved"] = True
                data["description"] = existing.get("description") or data["description"]
                data["tender_fee"] = existing.get("tender_fee") or data["tender_fee"]
                data["emd_amount"] = existing.get("emd_amount") or data["emd_amount"]
                if existing.get("documents"):
                    data["documents"] = existing["documents"]

            await self.collection.update_one(
                {"_id": existing["_id"]},
                {"$set": data}
            )
            return False, str(existing["_id"])
        else:
            data["scraped_at"] = now
            result = await self.collection.insert_one(data)
            return True, str(result.inserted_id)

    async def get_by_id(self, tender_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(tender_id)
            doc = await self.collection.find_one({"_id": oid})
            return self._convert_id(doc)
        except Exception:
            return None

    async def search_and_filter(self, params: TenderFilterParams) -> Dict[str, Any]:
        """
        Executes multi-criteria query and returns paginated results.
        """
        query: Dict[str, Any] = {}

        # 1. Text/Keyword search across title, description, reference_no, organisation
        if params.keyword and params.keyword.strip():
            kw = re.escape(params.keyword.strip())
            pattern = {"$regex": kw, "$options": "i"}
            query["$or"] = [
                {"title": pattern},
                {"description": pattern},
                {"reference_no": pattern},
                {"organisation": pattern},
                {"location": pattern}
            ]

        # 2. Source filter (e.g. CPPP, GeM)
        if params.source and params.source.strip() and params.source != "ALL":
            query["source"] = params.source.strip()

        # 3. Status filter (OPEN, CLOSED)
        if params.status and params.status.strip() and params.status != "ALL":
            query["status"] = params.status.strip()

        # 4. State / Location filter
        if params.state and params.state.strip():
            query["location"] = {"$regex": re.escape(params.state.strip()), "$options": "i"}

        # 5. Category filter
        if params.category and params.category.strip() and params.category != "ALL":
            query["category"] = {"$regex": re.escape(params.category.strip()), "$options": "i"}

        # 6. Organisation filter
        if params.organisation and params.organisation.strip():
            query["organisation"] = {"$regex": re.escape(params.organisation.strip()), "$options": "i"}

        # 7. Value Range
        if params.min_value is not None or params.max_value is not None:
            val_query: Dict[str, Any] = {}
            if params.min_value is not None:
                val_query["$gte"] = params.min_value
            if params.max_value is not None:
                val_query["$lte"] = params.max_value
            query["tender_value"] = val_query

        # 8. Date ranges
        if params.date_from is not None or params.date_to is not None:
            date_query: Dict[str, Any] = {}
            if params.date_from is not None:
                date_query["$gte"] = params.date_from
            if params.date_to is not None:
                date_query["$lte"] = params.date_to
            query["closing_date"] = date_query

        # Pagination & Sorting
        skip = (params.page - 1) * params.limit
        sort_field = params.sort_by if params.sort_by in ["closing_date", "publication_date", "tender_value", "scraped_at"] else "closing_date"
        sort_dir = pymongo.ASCENDING if params.sort_order == 1 else pymongo.DESCENDING

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort(sort_field, sort_dir).skip(skip).limit(params.limit)

        tenders = []
        async for doc in cursor:
            tenders.append(self._convert_id(doc))

        total_pages = (total + params.limit - 1) // params.limit if total > 0 else 1

        return {
            "items": tenders,
            "total": total,
            "page": params.page,
            "limit": params.limit,
            "total_pages": total_pages
        }

    async def get_stats(self) -> Dict[str, Any]:
        """
        Returns high-level statistics for scraped tenders:
        - Total count
        - Counts grouped by source
        - Counts grouped by status
        - Total estimated value
        """
        total = await self.collection.count_documents({})

        # Group by source
        pipeline_source = [
            {"$group": {"_id": "$source", "count": {"$sum": 1}}}
        ]
        source_counts = {}
        async for doc in self.collection.aggregate(pipeline_source):
            if doc["_id"]:
                source_counts[doc["_id"]] = doc["count"]

        # Group by status
        pipeline_status = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = {}
        async for doc in self.collection.aggregate(pipeline_status):
            if doc["_id"]:
                status_counts[doc["_id"]] = doc["count"]

        return {
            "total_tenders": total,
            "by_source": source_counts,
            "by_status": status_counts
        }
