from typing import Annotated

from fastapi import APIRouter, Depends, Path

from auth.auth_bearer import get_authenticated_user_data
from gojauntly.gojauntly import GoJauntlyApi
from schemas.gojauntly import (
    CuratedWalkRetrieve,
    CuratedWalksSearch,
    DynamicRoutesCircularCollection,
)
from utils.base_config import config

router = APIRouter(dependencies=[Depends(get_authenticated_user_data)], tags=["GoJauntly"])


client = GoJauntlyApi(
    key_id=config.gojauntly_key_id,
    secret_key=config.gojauntly_private_key,
    issuer_id=config.gojauntly_issuer_id,
)


@router.post("/curated-walks/search")
async def curated_walk_search(data: CuratedWalksSearch):
    response = client.curated_walk_search(data=data.model_dump())

    return response


@router.post("/curated-walks/{id}")
async def curated_walk_retrieve(
    id: Annotated[str, Path(description="ID of the walk")], data: CuratedWalkRetrieve
):
    response = client.curated_walk_retrieve(id=id, data=data.model_dump())

    return response


@router.post("/routing/circular/collection")
async def dynamic_routes_circular_collection(data: DynamicRoutesCircularCollection):
    response = client.dynamic_routes_circular_collection(data=data.model_dump())

    return response
