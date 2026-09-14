from fastapi import APIRouter
from typing import List
from app.schemas.category import CategoryResponse
from app.repositories.category_repository import CategoryRepository

router = APIRouter()

@router.get("", response_model=List[CategoryResponse])
async def read_categories():
    """Retrieve all categories hierarchy."""
    repo = CategoryRepository()
    return await repo.get_all()

