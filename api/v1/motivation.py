from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from crud.motivation_crud import UserMotivationCRUD
from schemas.motivation import (
    CreateUpdateUserMotivationRequest,
    UserMotivationResponse,
)
from utils.base_config import logger

router = APIRouter(prefix="/motivations", tags=["Motivations"])


@router.post("/", response_model=UserMotivationResponse, status_code=201)
async def create_user_motivation(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    new_motivation = crud.create_motivation(user_data["user_id"], payload)
    return new_motivation


@router.get("/", response_model=list[UserMotivationResponse])
async def get_all_motivations(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    return crud.get_all_by_user(user_data["user_id"])


@router.get("/{motivation_id}", response_model=UserMotivationResponse)
async def get_motivation_by_id(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    logger.info(f"Motivation ID: {motivation.id}")
    logger.info(f"User ID: {user_data['user_id']}")
    logger.info(f"condition: {str(motivation.user_id) != user_data['user_id']}")

    if not motivation or str(motivation.user_id) != user_data["user_id"]:
        raise HTTPException(status_code=404, detail="Motivation not found")

    return motivation


@router.put("/{motivation_id}", response_model=UserMotivationResponse)
async def update_user_motivation(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    if not motivation or str(motivation.user_id) != user_data["user_id"]:
        raise HTTPException(status_code=404, detail="Motivation not found")

    updated = crud.update_motivation(motivation, payload)
    return updated


@router.delete("/{motivation_id}", status_code=204)
async def delete_user_motivation(
    user_data: Annotated[dict, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    if not motivation or str(motivation.user_id) != user_data["user_id"]:
        raise HTTPException(status_code=404, detail="Motivation not found")

    crud.delete_motivation(motivation)
