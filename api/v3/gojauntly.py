from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, status

from auth.v3.dependencies import get_current_user
from gojauntly.gojauntly import GoJauntlyApi
from schemas.gojauntly import (
    CuratedWalkRetrieve,
    CuratedWalksSearch,
    DynamicRoutesCircularCollection,
)
from utils.base_config import config, logger
from utils.custom_exceptions import CustomHTTPException, ErrorCode

router = APIRouter(dependencies=[Depends(get_current_user)], tags=["GoJauntly"])

client = GoJauntlyApi(
    key_id=config.gojauntly_key_id,
    secret_key=config.gojauntly_private_key,
    issuer_id=config.gojauntly_issuer_id,
)

BAD_INPUT_STATUSES = {status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY}


def _call_gojauntly(request: Callable[..., Any], **kwargs) -> Any:
    """
    Calls GoJauntly and turns its errors into coded ones: bad input stays a 400, anything else
    is a 502, so an upstream 401 is never mistaken for the caller's own sign-in failing.
    """
    try:
        return request(**kwargs)
    except HTTPException as e:
        logger.error(f"GoJauntly request failed with status {e.status_code}")
        if e.status_code in BAD_INPUT_STATUSES:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code=ErrorCode.INVALID_REQUEST,
                error_message="GoJauntly rejected the request",
            ) from e
        raise CustomHTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.UPSTREAM_ERROR,
            error_message="GoJauntly request failed",
        ) from e


@router.post("/curated-walks/search")
def curated_walk_search(data: CuratedWalksSearch):
    return _call_gojauntly(client.curated_walk_search, data=data.model_dump())


@router.post("/curated-walks/{id}")
def curated_walk_retrieve(
    id: Annotated[str, Path(description="ID of the walk")], data: CuratedWalkRetrieve
):
    return _call_gojauntly(client.curated_walk_retrieve, id=id, data=data.model_dump())


@router.post("/routing/circular/collection")
def dynamic_routes_circular_collection(data: DynamicRoutesCircularCollection):
    return _call_gojauntly(client.dynamic_routes_circular_collection, data=data.model_dump())
