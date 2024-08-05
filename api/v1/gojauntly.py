from typing import Annotated

from fastapi import APIRouter, Depends, Path

from gojauntly.gojauntly import GoJauntlyApi
from service.auth_service import get_authenticated_user_data
from utils.base_config import config

from schemas.gojauntly import (
    CuratedWalkRetrieve,
    CuratedWalksSearch,
    DynamicRoutesCircularCollection,
)


router = APIRouter(dependencies=[Depends(get_authenticated_user_data)], tags=["GoJauntly"])


client = GoJauntlyApi(
    key_id=config.key_id,
    secret_key=config.prv_key,
    issuer_id=config.issuer_id
)


@router.post("/curated-walks/search")
async def curated_walk_search(data: CuratedWalksSearch):
    response = client.curated_walk_search(data=data.model_dump())

    return response


@router.post("/curated-walks/{id}")
async def curated_walk_retrieve(id: Annotated[str, Path(description="ID of the walk")], data: CuratedWalkRetrieve):
    response = client.curated_walk_retrieve(id=id, data=data.model_dump())

    return response


@router.post("/routing/circular/collection")
async def dynamic_routes_circular_collection(data: DynamicRoutesCircularCollection):
    response = client.dynamic_routes_circular_collection(data=data.model_dump())

    return response
