from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from auth.auth_bearer import get_authenticated_user_data
from crud.motivation_crud import UserMotivationCRUD
from models import User
from schemas.motivation import (
    CreateUpdateUserMotivationRequest,
    UserMotivationResponse,
)

router = APIRouter(prefix="/motivations", tags=["Motivations"])


@router.post("/", response_model=UserMotivationResponse, status_code=201)
async def create_user_motivation(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    new_motivation = crud.create_motivation(user.id, payload)
    return new_motivation


@router.get("/", response_model=list[UserMotivationResponse])
async def get_all_motivations(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    return crud.get_all_by_user(user.id)


@router.get("/{motivation_id}", response_model=UserMotivationResponse)
async def get_motivation_by_id(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    if not motivation or motivation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Motivation not found")

    return motivation


@router.put("/{motivation_id}", response_model=UserMotivationResponse)
async def update_user_motivation(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    payload: CreateUpdateUserMotivationRequest,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    if not motivation or motivation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Motivation not found")

    updated = crud.update_motivation(motivation, payload)
    return updated


@router.delete("/{motivation_id}", status_code=204)
async def delete_user_motivation(
    user: Annotated[User, Depends(get_authenticated_user_data)],
    motivation_id: UUID,
    crud: Annotated[UserMotivationCRUD, Depends()],
):
    motivation = crud.get_by_id(motivation_id)
    if not motivation or motivation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Motivation not found")

    crud.delete_motivation(motivation)
