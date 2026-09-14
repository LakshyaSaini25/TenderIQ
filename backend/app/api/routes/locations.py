from fastapi import APIRouter
from typing import List
from app.schemas.location import LocationResponse
from app.repositories.location_repository import LocationRepository

router = APIRouter()

@router.get("", response_model=List[LocationResponse])
async def read_locations():
    """Retrieve all locations."""
    repo = LocationRepository()
    return await repo.get_all()

