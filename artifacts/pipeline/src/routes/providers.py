from fastapi import APIRouter, Query

from pipeline.provider_status import get_provider_status

router = APIRouter(prefix="/pipeline/providers", tags=["providers"])


@router.get("/status")
async def provider_status(force_refresh: bool = Query(default=False)):
    return await get_provider_status(force_refresh=force_refresh)
