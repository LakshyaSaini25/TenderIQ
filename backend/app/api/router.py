from fastapi import APIRouter
from app.api.routes import health, sources, content, opportunities, categories, locations, ai, explore

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(explore.router, prefix="/explore", tags=["explore"])

# Future routes will be added here:
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(users.router, prefix="/users", tags=["users"])

