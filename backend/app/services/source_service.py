from fastapi import HTTPException
from app.repositories.source_repository import SourceRepository
from app.schemas.source import SourceCreate, SourceUpdate

class SourceService:
    def __init__(self):
        self.repo = SourceRepository()

    async def get_all_sources(self):
        return await self.repo.get_all()

    async def get_source(self, source_id: str):
        source = await self.repo.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return source

    async def create_source(self, source_in: SourceCreate):
        return await self.repo.create(source_in.model_dump())

    async def update_source(self, source_id: str, source_in: SourceUpdate):
        update_data = source_in.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")
            
        updated = await self.repo.update(source_id, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="Source not found")
        return updated

    async def delete_source(self, source_id: str):
        deleted = await self.repo.delete(source_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Source not found")
        return True

